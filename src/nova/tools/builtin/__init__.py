"""Built-in Nova tools (shell, open_app, clipboard, etc.)."""

from nova.tools.builtin import open_app as _open_app
from nova.tools.builtin import shell as _shell

DESTRUCTIVE_VERBS = _shell.DESTRUCTIVE_VERBS
RunShellResult = _shell.RunShellResult
classify_command = _shell.classify_command
run_shell = _shell.run_shell

OpenResult = _open_app.OpenResult
open_app = _open_app.open_app

__all__ = [
    "DESTRUCTIVE_VERBS",
    "OpenResult",
    "RunShellResult",
    "classify_command",
    "open_app",
    "run_shell",
]
