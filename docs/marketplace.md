# Plugin marketplace

Curated MCP servers Nova can talk to out of the box.  Each entry is
one click — Nova reads this file at startup and shows the install
button next to the description in the Settings → MCPs page.

## How "one-click install" works

Nova reads the YAML/JSON manifest a marketplace entry points to,
asks the user to confirm, then runs the installer:

- **pip** — `pip install <package>` then auto-discovery via the
  `nova.tools` / `nova.mcp_servers` entry points (`nova.plugins`).
- **stdio** — drops the command into `~/.config/nova/mcps.json` so
  the launcher spawns it on next start.
- **container** — pulls the Docker image and adds a stdio command
  that runs it with the right ports / volumes.

Every install passes through `nova.tools.approval` so the user gets
an auth prompt before the new tool can run.

## Featured

| Server | Tools | Install kind | Manifest |
|---|---|---|---|
| **filesystem** | `fs.read`, `fs.write`, `fs.search` | stdio | `nova-mcp-fs` |
| **git** | `git.clone`, `git.commit`, `git.pr` | pip | `nova-mcp-git` |
| **postgres** | `pg.query`, `pg.schema` | container | `ghcr.io/anthropic/mcp-postgres` |
| **slack** | `slack.send`, `slack.history` | pip | `nova-mcp-slack` |
| **notion** | `notion.search`, `notion.create_page` | pip | `nova-mcp-notion` |
| **linear** | `linear.create_issue`, `linear.search` | pip | `nova-mcp-linear` |
| **playwright** | `browser.navigate`, `browser.click` | container | `mcr.microsoft.com/playwright` |
| **home-assistant** | `home.list`, `home.call_service` | builtin | `nova.integrations.home_assistant` |
| **spotify** | `music.play`, `music.pause` | builtin | `nova.integrations.music` |
| **obsidian** | `notes.create`, `notes.search` | builtin | `nova.integrations.notes` |

## Submitting yours

1. Publish the package on PyPI or push a Docker image.
2. Add a row to this file with a one-line description of what it does.
3. Open a PR.  Maintainers review it for the safety policy (no surprise
   network targets, the auth flow goes through Nova's keystore, etc.)
   then merge.

The marketplace is just markdown — there's no central server, no
analytics, no pay-to-feature.  If you don't want your plugin listed
here you can ship the manifest on your own site; users add it via
**Settings → MCPs → Add custom URL**.

## Verification badges

Maintainers tag entries with these badges (rendered in the GUI):

- ✅ **Verified** — maintainers reviewed the source + signed releases
- 🔒 **Local-only** — the plugin makes no outbound network calls
- 🧪 **Beta** — recently added, expect breakage
- 🏷️ **Self-hosted** — runs against your own server (HA, Postgres, etc.)
