"""The three read calls. Every function takes an injectable `http` so tests run on recorded fixtures.

Only GET reports from App Store Connect and RevenueCat, and one read-only HogQL query to PostHog.
Nothing is written to any API and nothing is sent anywhere else.
"""
import csv
import datetime as dt
import gzip
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import keys

ASC_BASE = "https://api.appstoreconnect.apple.com"
RC_BASE = "https://api.revenuecat.com"
MAX_DAYS = 30

# Sales report product types that count as a first-time download (Apple's Product Type Identifiers).
FIRST_DOWNLOAD_TYPES = {"1", "1F", "1T", "F1", "1E", "1EP", "1EU"}


class NoData(Exception):
    """The API answered 404: no report for that day."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # a redirect would carry the Authorization header to another host


_opener = urllib.request.build_opener(_NoRedirect)


def default_http(method, url, headers=None, body=None, timeout=60):
    """(status, bytes). HTTPS only."""
    if not url.startswith("https://"):
        raise ValueError("only https URLs are allowed")
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def check_days(days):
    if not isinstance(days, int) or not 1 <= days <= MAX_DAYS:
        raise ValueError(f"days must be a whole number from 1 to {MAX_DAYS}")
    return days


def windows(days, today=None):
    """(this_start, this_end, prev_start, prev_end), whole days ending yesterday (UTC); both windows `days` long."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    this_end = today - dt.timedelta(days=1)
    this_start = this_end - dt.timedelta(days=days - 1)
    prev_end = this_start - dt.timedelta(days=1)
    prev_start = prev_end - dt.timedelta(days=days - 1)
    return this_start, this_end, prev_start, prev_end


def _span(a, b):
    return {"from": a.isoformat(), "to": b.isoformat()}


def _day_list(a, b):
    return [a + dt.timedelta(days=i) for i in range((b - a).days + 1)]


# ---------------------------------------------------------------- App Store Connect

def asc_token(now=None):
    import jwt  # PyJWT with cryptography for ES256
    key_path = Path(keys.get("ASC_KEY_PATH")).expanduser()
    now = int(now or time.time())
    return jwt.encode(
        {"iss": keys.get("ASC_ISSUER_ID"), "iat": now, "exp": now + 900, "aud": "appstoreconnect-v1"},
        key_path.read_text(), algorithm="ES256", headers={"kid": keys.get("ASC_KEY_ID"), "typ": "JWT"},
    )


def asc_sales_day(day, http=default_http, token=None, vendor=None):
    """Rows of the DAILY SALES SUMMARY report for one day. Raises NoData on 404."""
    q = urllib.parse.urlencode({
        "filter[frequency]": "DAILY", "filter[reportType]": "SALES", "filter[reportSubType]": "SUMMARY",
        "filter[vendorNumber]": vendor or keys.get("ASC_VENDOR_NUMBER"), "filter[reportDate]": day.isoformat(),
    })
    status, raw = http("GET", f"{ASC_BASE}/v1/salesReports?{q}",
                       {"Authorization": f"Bearer {token or asc_token()}", "Accept": "application/a-gzip"})
    if status == 404:
        raise NoData(day.isoformat())
    if status >= 400:
        raise RuntimeError(f"App Store Connect answered HTTP {status} for the sales report")
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8", errors="replace")), delimiter="\t"))


def _matches(row, app):
    if not app:
        return True
    needle = app.strip().lower()
    return any(needle in (row.get(f) or "").lower() for f in ("Title", "SKU", "Apple Identifier"))


def _collect(a, b, app, http, token, vendor):
    rows, missing = [], []
    for day in _day_list(a, b):
        try:
            rows += [r for r in asc_sales_day(day, http, token, vendor) if _matches(r, app)]
        except NoData:
            missing.append(day.isoformat())
    return rows, missing


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def downloads(app=None, days=7, http=default_http, today=None):
    check_days(days)
    ts, te, ps, pe = windows(days, today)
    token, vendor = asc_token(), keys.get("ASC_VENDOR_NUMBER")
    out = {"source": "App Store Connect Sales and Trends", "app_filter": app, "days": days, "unit": "first-time downloads"}
    for label, (a, b) in (("this_window", (ts, te)), ("previous_window", (ps, pe))):
        rows, missing = _collect(a, b, app, http, token, vendor)
        total = sum(_num(r.get("Units")) for r in rows if (r.get("Product Type Identifier") or "").strip() in FIRST_DOWNLOAD_TYPES)
        out[label] = {**_span(a, b), "downloads": int(total), "days_without_report": missing}
    incomplete = out["this_window"]["days_without_report"] or out["previous_window"]["days_without_report"]
    out["change"] = None if incomplete else out["this_window"]["downloads"] - out["previous_window"]["downloads"]
    if incomplete:
        out["change_note"] = "Withheld: a window has days without an Apple report (often yesterday, not posted yet). Do not compare the totals."
    return out


def proceeds(app=None, days=7, http=default_http, today=None):
    check_days(days)
    ts, te, ps, pe = windows(days, today)
    token, vendor = asc_token(), keys.get("ASC_VENDOR_NUMBER")
    out = {"source": "App Store Connect Sales and Trends", "app_filter": app, "days": days,
           "unit": "developer proceeds by currency, as Apple reports them (units x proceeds per unit)",
           "note": "Compare windows only when days_without_report is empty in both."}
    for label, (a, b) in (("this_window", (ts, te)), ("previous_window", (ps, pe))):
        rows, missing = _collect(a, b, app, http, token, vendor)
        by_cur = {}
        for r in rows:
            cur = (r.get("Currency of Proceeds") or "").strip() or "unknown"
            by_cur[cur] = by_cur.get(cur, 0.0) + _num(r.get("Units")) * _num(r.get("Developer Proceeds"))
        by_cur = {c: round(v, 2) for c, v in by_cur.items() if round(v, 2) != 0}  # free-app rows add nothing
        out[label] = {**_span(a, b), "proceeds": by_cur, "days_without_report": missing}
    return out


# ---------------------------------------------------------------- RevenueCat v2

_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _rc_get(path, http):
    status, raw = http("GET", RC_BASE + path, {"Authorization": f"Bearer {keys.get('REVENUECAT_API_KEY')}"})
    if status >= 400:
        raise RuntimeError(f"RevenueCat answered HTTP {status}")
    return json.loads(raw)


def revenuecat_projects(http=default_http):
    """Project ids and names, so you can pass one to subscribers()."""
    data = _rc_get("/v2/projects", http)
    return [{"id": p.get("id"), "name": p.get("name")} for p in data.get("items", [])]


def subscribers(project, http=default_http, today=None, days=7):
    check_days(days)
    if not _ID.match(project or ""):
        raise ValueError("project must be a RevenueCat project id (letters, digits, - and _)")
    ts, te, ps, pe = windows(days, today)
    overview = _rc_get(f"/v2/projects/{project}/metrics/overview", http)
    metrics = {m["id"]: m.get("value") for m in overview.get("metrics", [])}
    q = urllib.parse.urlencode({"start_date": ps.isoformat(), "end_date": te.isoformat(), "resolution": "day"})
    chart = _rc_get(f"/v2/projects/{project}/charts/actives?{q}", http)
    by_day = {}
    for v in chart.get("values", []):
        if v.get("measure") == 0:
            by_day[dt.datetime.fromtimestamp(v["cohort"], dt.timezone.utc).date()] = v.get("value")
    return {
        "source": "RevenueCat v2", "currency": overview.get("currency"), "days": days,
        "now": {k: metrics.get(k) for k in ("active_subscriptions", "active_trials", "mrr", "revenue", "new_customers")},
        "now_note": "Overview figures as RevenueCat reports them; revenue and new_customers cover the last 28 days.",
        "active_subscriptions_this_window_end": {"on": te.isoformat(), "value": by_day.get(te)},
        "active_subscriptions_previous_window_end": {"on": pe.isoformat(), "value": by_day.get(pe)},
    }


# ---------------------------------------------------------------- PostHog HogQL

_EVENT = re.compile(r"^[A-Za-z0-9_$ .:/-]{1,100}$")
_PROJECT = re.compile(r"^[0-9]{1,12}$")


def _hogql_literal(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def events(project, names=None, days=7, http=default_http, today=None):
    check_days(days)
    if not _PROJECT.match(str(project or "")):
        raise ValueError("project must be the numeric PostHog project id")
    names = names or []
    for n in names:
        if not _EVENT.match(n):
            raise ValueError(f"event name {n!r} has characters this tool does not allow")
    host = keys.get("POSTHOG_HOST", required=False, default="https://us.posthog.com").rstrip("/")
    if not host.startswith("https://"):
        raise ValueError("POSTHOG_HOST must start with https://")
    ts, te, ps, pe = windows(days, today)
    where = f" AND event IN ({', '.join(_hogql_literal(n) for n in names)})" if names else ""
    # Dates are our own isoformat strings, never user text.
    query = (
        "SELECT event, "
        f"countIf(toDate(toTimeZone(timestamp, 'UTC')) >= toDate('{ts}') AND toDate(toTimeZone(timestamp, 'UTC')) <= toDate('{te}')) AS this_window, "
        f"countIf(toDate(toTimeZone(timestamp, 'UTC')) >= toDate('{ps}') AND toDate(toTimeZone(timestamp, 'UTC')) <= toDate('{pe}')) AS previous_window "
        f"FROM events WHERE toDate(toTimeZone(timestamp, 'UTC')) >= toDate('{ps}') AND toDate(toTimeZone(timestamp, 'UTC')) <= toDate('{te}'){where} "
        "GROUP BY event ORDER BY this_window DESC LIMIT 50"
    )
    status, raw = http("POST", f"{host}/api/projects/{project}/query/",
                       {"Authorization": f"Bearer {keys.get('POSTHOG_API_KEY')}", "Content-Type": "application/json"},
                       json.dumps({"query": {"kind": "HogQLQuery", "query": query}}).encode())
    if status >= 400:
        raise RuntimeError(f"PostHog answered HTTP {status}")
    rows = json.loads(raw).get("results", [])
    return {
        "source": "PostHog HogQL", "days": days, "this_window": _span(ts, te), "previous_window": _span(ps, pe),
        "events": [{"event": r[0], "this_window": int(r[1]), "previous_window": int(r[2]),
                    "change": int(r[1]) - int(r[2])} for r in rows],
        "note": "Top 50 events by this-window count." if not names else "Only the named events.",
    }
