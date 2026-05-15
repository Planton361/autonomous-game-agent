import typer
from rich.console import Console

from fh_agent import __version__

app = typer.Typer(
    add_completion=False,
    help="Fear & Hunger no-spoiler agent tooling.",
)
console = Console()


@app.callback()
def root(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show package version and exit.",
    ),
) -> None:
    """Run fh-agent commands."""
    if version:
        console.print(f"fh-agent {__version__}")
        raise typer.Exit()


def main() -> None:
    app()
