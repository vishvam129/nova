# Nova community

Where to ask, where to suggest, what to expect back.

## Channels

| Channel | Purpose |
|---|---|
| GitHub Issues | Bug reports + scoped feature requests with reproduction steps |
| GitHub Discussions | Open-ended questions, show-and-tell, design proposals |
| Discord (`#nova`) | Real-time chat, voice debugging, MCP-author meetups |
| Mailing list (`announce@`) | Release notes only — no traffic between releases |

Links live in README.md and `pyproject.toml [project.urls]` so package
managers surface them too.

## Public roadmap

Maintained as a single GitHub Project board with three columns:

- **Now** — features actively being implemented this milestone
- **Next** — accepted for the following milestone, design landed
- **Later** — accepted in principle, design pending or blocked on upstream

Anything not on the board has not been accepted; opening an issue is
how something gets considered.  Vote on cards with the existing
GitHub reaction set.

## Issue triage SLA

These are *targets*, not promises.  Maintainers are unpaid.

| Severity | Response | Resolution target |
|---|---|---|
| **S0** — data loss / safety | < 24 h | < 7 days |
| **S1** — major regression | < 3 days | < 30 days |
| **S2** — non-blocking bug | < 7 days | next minor release |
| **S3** — feature request | < 14 days (accept/decline) | based on roadmap |

A bot labels new issues with a triage timer; if the timer expires
without a maintainer comment, it's escalated to `triage-stale`.

## Discussions etiquette

- Search existing issues + discussions first.
- One topic per thread.
- "Doesn't work" is not a bug report — include the OS, Nova version,
  the exact command/voice prompt, and the audit log line if relevant.
- Treat the chat / Discord like a public archive — don't paste secrets.

## Becoming a maintainer

Open a PR.  Reviewers are picked from CONTRIBUTORS.md based on whoever
last touched the area.  After two merged non-trivial PRs you'll be
offered triage rights; after five, full commit rights.

## Code of conduct

The standard Contributor Covenant v2.1 applies.  Reports go to
`conduct@nova.dev` (private — only the conduct team reads it).
