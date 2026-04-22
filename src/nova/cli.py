"""Nova CLI entrypoint with subcommands."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from nova import __version__
from nova.config import default_config_path, load_config
from nova.db import open_store

app = typer.Typer(
    help="Nova: cross-device AI assistant.",
    no_args_is_help=True,
    add_completion=False,
)
devices_app = typer.Typer(help="Manage paired devices.", no_args_is_help=True)
mcp_app = typer.Typer(help="Manage MCP servers.", no_args_is_help=True)
memory_app = typer.Typer(help="Inspect and export memory.", no_args_is_help=True)
config_app = typer.Typer(help="View and validate configuration.", no_args_is_help=True)

app.add_typer(devices_app, name="devices")
app.add_typer(mcp_app, name="mcp")
app.add_typer(memory_app, name="memory")
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"nova {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option("--version", "-v", callback=_version_callback, is_eager=True),
    ] = False,
) -> None:
    """Nova command-line entrypoint."""


@app.command()
def run() -> None:
    """Start the brain service (stub)."""
    cfg = load_config()
    typer.echo(f"nova: brain starting on {cfg.server.host}:{cfg.server.port} (stub)")


@app.command()
def eval() -> None:
    """Run the personal task eval suite (stub)."""
    typer.echo("nova eval: no suite yet (stub)")


@devices_app.command("list")
def devices_list() -> None:
    cfg = load_config()
    conn = open_store(cfg.data_dir / "nova.db")
    rows = conn.execute("SELECT id, name, platform FROM devices ORDER BY paired_at").fetchall()
    if not rows:
        typer.echo("no paired devices")
        return
    for r in rows:
        typer.echo(f"{r['id']}\t{r['name']}\t{r['platform']}")


@mcp_app.command("list")
def mcp_list() -> None:
    typer.echo("(no MCP servers configured)")


@mcp_app.command("add")
def mcp_add(url: str) -> None:
    typer.echo(f"mcp add {url}: not implemented yet")


@memory_app.command("export")
def memory_export() -> None:
    typer.echo("memory export: not implemented yet")


@config_app.command("show")
def config_show() -> None:
    cfg = load_config()
    typer.echo(json.dumps(cfg.model_dump(mode="json"), indent=2, default=str))


@config_app.command("path")
def config_path() -> None:
    typer.echo(str(default_config_path()))


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
