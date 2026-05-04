# Contributing to Nova

Thanks for considering it. This guide is short on purpose.

## Setup

```bash
git clone git@github.com:vishvam129/nova.git
cd nova
uv sync
uv run pytest -q          # should pass before you touch anything
uv run ruff check src tests
uv run mypy src
```

## Code style

- Python 3.11+, `from __future__ import annotations` everywhere.
- Ruff + mypy strict are CI-blocking. Run them locally before pushing.
- Type-annotate all public functions; tests can skip return types.
- Prefer Protocols + dataclasses over inheritance.
- Lazy-import optional native deps (sounddevice, onnxruntime, pynacl, …)
  inside the function that needs them so module import stays cheap.
- One module per concern. If a file passes 250 lines, split it.

## Tests

- Every new module ships a `tests/test_<module>.py`.
- Tests use only stdlib + pytest. Mock OS / network at the boundary.
- No tests that require a microphone, GPU, or network in the default suite.
  Use `pytest.importorskip(...)` or the `slow` / `e2e` markers.

## Pull requests

- Branch off `main` with the prefix `nova/` (the GitOps integration
  refuses to commit anywhere else).
- One feature per PR. Smaller is faster to land.
- Fill the PR template (below). Specifically: link the GitHub issue
  number, list the modules touched, and paste the test output.

## PR template (`.github/pull_request_template.md`)

```markdown
## What & why
<one sentence describing the change and the user-visible effect>

Fixes #<issue>

## Modules touched
- src/nova/...
- tests/...

## Test output
<paste of `uv run pytest -q`>

## Checklist
- [ ] Tests added / updated
- [ ] `ruff check` clean
- [ ] `mypy src` clean
- [ ] Docs updated (if user-facing)
```

## Good first issues

Maintainers tag tractable issues with these labels:

- `good first issue` — small, well-scoped, no surrounding refactor needed
- `docs` — improve a docstring, README section, or example
- `tests` — add coverage for an existing untested code path
- `mcp-author` — write a new built-in MCP server (great way to learn
  the contract)

Sort the issue tracker by these labels to find a starting point.

## Don't

- Don't push directly to `main`.
- Don't bypass the audit log or the safety policy in agent code.
- Don't add a dependency without a one-line justification in the PR.
- Don't add tracking, telemetry, or phone-home calls outside
  `nova.devops.telemetry` (which is opt-in by design).
