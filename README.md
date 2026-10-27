# indie-metrics-mcp

Ask Claude how your apps are doing. This is a small MCP server that reads your own App Store Connect sales, RevenueCat subscribers and PostHog events, and answers with this week against last week. It runs on your machine with your keys.

Shipping an app and want the checklist? The [App Store launch kit](https://www.inzention.com/app-store-launch-kit).

## Tools

| Tool | Answers |
|------|---------|
| `downloads(app?, days)` | First-time downloads, last `days` against the `days` before (App Store Connect Sales and Trends) |
| `proceeds(app?, days)` | Developer proceeds by currency, same two windows |
| `revenuecat_projects()` | Your RevenueCat project ids |
| `subscribers(project, days)` | Active subscriptions, trials, MRR and 28-day revenue now; active subscriptions at the end of each window |
| `events(project, names?, days)` | PostHog event counts, same two windows (HogQL) |

`days` is 1 to 30. Windows are whole days ending yesterday (UTC). Apple posts a day's report the next day, so a missing day is listed under `days_without_report`.

## Set up

1. Install Python 3.10 or newer.
2. `git clone` this repository and `cd` into it.
3. `python3 -m venv .venv && .venv/bin/pip install .`
4. App Store Connect: in Users and Access, Integrations, create a key with the Sales role. Download the `.p8` file and note the key id, the issuer id and your vendor number (Payments and Financial Reports).
5. RevenueCat: create a v2 secret API key with read-only access to projects, customers and charts.
6. PostHog: create a personal API key with read access to query. Note your numeric project id.
7. Give the server your keys as environment variables or as macOS Keychain items (service `indie-metrics.<NAME>`; `security add-generic-password -s indie-metrics.<NAME> -a "$USER" -w` prompts for the value). Names: `ASC_KEY_ID`, `ASC_ISSUER_ID`, `ASC_KEY_PATH` (path to the `.p8`), `ASC_VENDOR_NUMBER`, `REVENUECAT_API_KEY`, `POSTHOG_API_KEY`, and optionally `POSTHOG_HOST` (default `https://us.posthog.com`; use `https://eu.posthog.com` for the EU cloud).
8. Add it to Claude Code: `claude mcp add indie-metrics -- /full/path/to/.venv/bin/indie-metrics-mcp`. Any MCP client that starts a stdio server works the same way.
9. Ask: "How many downloads did I get this week against last week?"

You only need the keys for the sources you use. A tool without its key says which setting is missing.

## What this will not do

- No writes. It only reads; it never changes an app, a price, a product or an event.
- No hosted service, no account, no telemetry. It talks to Apple, RevenueCat and your PostHog host and nothing else.
- No Google Play in this version.
- No keys in this repository, and none printed in output or errors.
- No guesses. When an API answers with an error the tool says so; it does not fill the gap.

## Tests

`pip install ".[test]" && pytest`. The tests use recorded response shapes with invented ids and a throwaway signing key made at test time.

## Licence

MIT. Dependency licences: [LICENCES.md](LICENCES.md).
