"""Nova CLI entrypoint."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-v", "--version"}:
        from nova import __version__

        print(f"nova {__version__}")
        return 0
    print("nova: cross-device AI assistant (scaffold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
