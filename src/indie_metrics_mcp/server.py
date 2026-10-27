"""MCP server. Five read-only tools over stdio."""
from mcp.server.mcpserver import MCPServer

from . import sources

mcp = MCPServer("indie-metrics")


@mcp.tool()
def downloads(app: str | None = None, days: int = 7) -> dict:
    """First-time downloads from App Store Connect Sales and Trends: the last `days` whole days against the `days` before.
    `app` filters by title, SKU or Apple id (substring); leave it out for all apps. Days run 1 to 30."""
    return sources.downloads(app, days)


@mcp.tool()
def proceeds(app: str | None = None, days: int = 7) -> dict:
    """Developer proceeds from App Store Connect Sales and Trends, by currency: the last `days` against the `days` before.
    `app` filters by title, SKU or Apple id (substring); leave it out for all apps. Days run 1 to 30."""
    return sources.proceeds(app, days)


@mcp.tool()
def revenuecat_projects() -> list:
    """The RevenueCat projects this key can read (id and name). Use an id with `subscribers`."""
    return sources.revenuecat_projects()


@mcp.tool()
def subscribers(project: str, days: int = 7) -> dict:
    """RevenueCat active subscriptions, trials, MRR and 28-day revenue now, plus active subscriptions at the end of this
    window against the end of the previous one. `project` is a RevenueCat project id."""
    return sources.subscribers(project, days=days)


@mcp.tool()
def events(project: str, names: list[str] | None = None, days: int = 7) -> dict:
    """PostHog event counts: the last `days` whole days against the `days` before. `project` is the numeric PostHog
    project id; `names` limits it to those event names, otherwise the top 50 events."""
    return sources.events(project, names, days)


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()
