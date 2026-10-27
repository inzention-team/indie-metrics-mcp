# Dependency licences

Checked 2026-10-28 from each package's installed metadata (`pip show -v`).

| Package | Version checked | Licence | Why |
|---------|-----------------|---------|-----|
| mcp (Model Context Protocol Python SDK) | 2.3.0 | MIT | Serves the tools to Claude |
| PyJWT | 2.15.1 | MIT | Signs the App Store Connect token (ES256) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | Needed by PyJWT for ES256 |
| pytest (tests only) | 9.1.1 | MIT | Test runner |

Transitive dependencies come with `mcp` and `cryptography`; none is bundled in this repository. To list them for your install run `pip list`, then `pip show <name>` for each.
