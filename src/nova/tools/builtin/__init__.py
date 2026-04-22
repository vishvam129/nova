"""Built-in Nova tools (shell, open_app, clipboard, etc.)."""

from nova.tools.builtin import shell as _shell

DESTRUCTIVE_VERBS = _shell.DESTRUCTIVE_VERBS
RunShellResult = _shell.RunShellResult
classify_command = _shell.classify_command
run_shell = _shell.run_shell

__all__ = [
    "DESTRUCTIVE_VERBS",
    "RunShellResult",
    "classify_command",
    "run_shell",
]
