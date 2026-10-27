import datetime as dt
import gzip
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from indie_metrics_mcp import keys, sources

FIX = Path(__file__).parent / "fixtures"
TODAY = dt.date(2026, 10, 28)  # windows end 2026-10-27


@pytest.fixture(autouse=True)
def fake_env(tmp_path, monkeypatch):
    """A throwaway ES256 key made here, so no key material lives in the repo."""
    pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    key = tmp_path / "test-key.p8"
    key.write_bytes(pem)
    for k, v in {"ASC_KEY_ID": "TESTKEYID1", "ASC_ISSUER_ID": "00000000-0000-0000-0000-000000000000",
                 "ASC_KEY_PATH": str(key), "ASC_VENDOR_NUMBER": "99999999", "REVENUECAT_API_KEY": "sk_test_fake",
                 "POSTHOG_API_KEY": "phx_test_fake"}.items():
        monkeypatch.setenv(k, v)


def asc_http(days_with_report):
    calls = []

    def http(method, url, headers=None, body=None, timeout=60):
        calls.append((method, url))
        assert method == "GET"
        day = url.split("filter%5BreportDate%5D=")[1][:10]
        if day in days_with_report:
            return 200, gzip.compress((FIX / "sales_day.tsv").read_bytes())
        return 404, b""
    http.calls = calls
    return http


def test_downloads_counts_first_downloads_only_and_compares_windows():
    # 2026-10-27 is in this window (7 days), 2026-10-15 in the previous one
    http = asc_http({"2026-10-27", "2026-10-15"})
    out = sources.downloads(None, 7, http, TODAY)
    assert out["this_window"]["downloads"] == 8      # 3 + 5; the subscription row (IAY) is not a download
    assert out["previous_window"]["downloads"] == 8
    assert out["change"] is None and "Withheld" in out["change_note"]
    assert len(out["this_window"]["days_without_report"]) == 6
    assert len(http.calls) == 14


def test_downloads_app_filter_matches_title_sku_or_id():
    http = asc_http({"2026-10-27"})
    assert sources.downloads("alpha", 7, http, TODAY)["this_window"]["downloads"] == 3
    assert sources.downloads("1000000003", 7, http, TODAY)["this_window"]["downloads"] == 5


def test_proceeds_multiplies_units_by_proceeds_per_unit_by_currency():
    out = sources.proceeds(None, 7, asc_http({"2026-10-27"}), TODAY)
    assert out["this_window"]["proceeds"] == {"USD": 5.0}
    assert out["previous_window"]["proceeds"] == {}


@pytest.mark.parametrize("days", [0, 31, -1, "7", None])
def test_days_are_bounded(days):
    with pytest.raises(ValueError):
        sources.downloads(None, days, asc_http(set()), TODAY)


def test_server_error_is_surfaced_not_swallowed():
    def boom(method, url, headers=None, body=None, timeout=60):
        return 500, b"x"
    with pytest.raises(RuntimeError):
        sources.downloads(None, 1, boom, TODAY)


def rc_http(method, url, headers=None, body=None, timeout=60):
    assert method == "GET" and headers["Authorization"] == "Bearer sk_test_fake"
    if "metrics/overview" in url:
        return 200, (FIX / "rc_overview.json").read_bytes()
    if "charts/actives" in url:
        return 200, (FIX / "rc_actives.json").read_bytes()
    if url.endswith("/v2/projects"):
        return 200, json.dumps({"items": [{"id": "projFAKE1", "name": "Example"}]}).encode()
    return 404, b""


def test_subscribers_now_and_window_ends():
    out = sources.subscribers("projFAKE1", rc_http, TODAY)
    assert out["now"]["active_subscriptions"] == 31 and out["now"]["mrr"] == 142.5
    assert out["active_subscriptions_this_window_end"] == {"on": "2026-10-27", "value": 31}
    assert out["active_subscriptions_previous_window_end"] == {"on": "2026-10-20", "value": 24}


def test_subscribers_rejects_bad_project_id():
    with pytest.raises(ValueError):
        sources.subscribers("../x?y=1", rc_http, TODAY)


def test_revenuecat_projects_lists_ids():
    assert sources.revenuecat_projects(rc_http) == [{"id": "projFAKE1", "name": "Example"}]


def test_events_builds_read_only_query_and_compares():
    seen = {}

    def http(method, url, headers=None, body=None, timeout=60):
        seen.update(method=method, url=url, body=json.loads(body))
        return 200, (FIX / "posthog_query.json").read_bytes()
    out = sources.events("12345", ["paywall_viewed", "Screen: Home"], 7, http, TODAY)
    q = seen["body"]["query"]["query"]
    assert seen["url"] == "https://us.posthog.com/api/projects/12345/query/"
    assert q.startswith("SELECT event,") and "'Screen: Home'" in q
    assert out["events"][0] == {"event": "paywall_viewed", "this_window": 40, "previous_window": 25, "change": 15}


@pytest.mark.parametrize("name", ["a'; DROP", "x" * 101, "a\nb", ""])
def test_events_rejects_unsafe_names(name):
    with pytest.raises(ValueError):
        sources.events("12345", [name], 7, None, TODAY)


def test_events_rejects_bad_project_and_http_host(monkeypatch):
    with pytest.raises(ValueError):
        sources.events("12345/../x", None, 7, None, TODAY)
    monkeypatch.setenv("POSTHOG_HOST", "http://insecure.example")
    with pytest.raises(ValueError):
        sources.events("12345", None, 7, None, TODAY)


def test_missing_key_message_names_setting_not_value(monkeypatch):
    monkeypatch.delenv("REVENUECAT_API_KEY")
    monkeypatch.setattr(keys.sys, "platform", "linux")
    with pytest.raises(keys.MissingKey) as e:
        sources.revenuecat_projects(rc_http)
    assert "REVENUECAT_API_KEY" in str(e.value)


def test_default_http_refuses_non_https():
    with pytest.raises(ValueError):
        sources.default_http("GET", "http://example.com")


def test_keychain_fallback(monkeypatch):
    monkeypatch.delenv("POSTHOG_API_KEY")
    monkeypatch.setattr(keys.sys, "platform", "darwin")

    class R:
        returncode, stdout = 0, "from-keychain\n"
    monkeypatch.setattr(keys.subprocess, "run", lambda cmd, **kw: (setattr(R, "cmd", cmd), R)[1])
    assert keys.get("POSTHOG_API_KEY") == "from-keychain"
    assert R.cmd[3] == "indie-metrics.POSTHOG_API_KEY"


def test_downloads_change_given_when_all_days_reported():
    every = {(TODAY - dt.timedelta(days=i)).isoformat() for i in range(1, 15)}
    out = sources.downloads(None, 7, asc_http(every), TODAY)
    assert out["change"] == 0 and "change_note" not in out
