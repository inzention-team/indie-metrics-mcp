# Dependency licences

Checked 2026-10-28 from each package's installed metadata (`pip show -v`).

| Package | Version checked | Licence | Why |
|---------|-----------------|---------|-----|
| mcp (Model Context Protocol Python SDK) | 2.3.0 | MIT | Serves the tools to Claude |
| PyJWT | 2.15.1 | MIT | Signs the App Store Connect token (ES256) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Needed by PyJWT for ES256 |
| pytest (tests only) | 9.1.1 | MIT | Test runner |

## Transitive dependencies

These come with the packages above. None is bundled in this repository; pip installs them. Checked on a clean install of `indie-metrics-mcp[test]` with Python 3.15. Every licence is permissive and none is copyleft.

| Package | Version checked | Licence | Comes with |
|---------|-----------------|---------|------------|
| annotated-types | 0.8.0 | MIT | mcp |
| anyio | 4.15.1 | MIT | mcp |
| attrs | 26.1.0 | MIT | mcp |
| cffi | 2.1.1 | MIT-0 | cryptography |
| click | 8.5.0 | BSD-3-Clause | mcp |
| h11 | 0.16.0 | MIT | mcp |
| httpcore2 | 2.16.0 | BSD-3-Clause | mcp |
| httpx2 | 2.16.0 | BSD-3-Clause | mcp |
| idna | 3.20 | BSD-3-Clause | mcp |
| iniconfig | 2.3.1 | MIT | pytest (tests only) |
| jsonschema | 4.26.0 | MIT | mcp |
| jsonschema-specifications | 2025.9.1 | MIT | mcp |
| mcp-types | 2.3.0 | MIT | mcp |
| opentelemetry-api | 1.45.1 | Apache-2.0 | mcp |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | pytest (tests only) |
| pluggy | 1.7.0 | MIT | pytest (tests only) |
| pycparser | 3.12 | BSD-3-Clause | cryptography |
| pydantic | 2.14.1 | MIT | mcp |
| pydantic_core | 2.50.1 | MIT | mcp |
| Pygments | 2.21.0 | BSD-2-Clause | pytest (tests only) |
| python-multipart | 0.0.32 | Apache-2.0 | mcp |
| referencing | 0.37.0 | MIT | mcp |
| rpds-py | 2026.9.1 | MIT | mcp |
| sse-starlette | 3.6.0 | BSD-3-Clause | mcp |
| starlette | 1.10.0 | BSD-3-Clause | mcp |
| truststore | 0.10.5 | MIT | mcp |
| typing-inspection | 0.4.4 | MIT | mcp |
| typing_extensions | 4.16.0 | PSF-2.0 | mcp |
| uvicorn | 0.54.0 | BSD-3-Clause | mcp |

Versions change with your install. To check yours, run `pip list`, then `pip show <name>` for each.
