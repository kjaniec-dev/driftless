from pathlib import Path

import typer

from driftless.engine import compute_plan
from driftless.formatters.json_out import format_json
from driftless.formatters.table import print_plan
from driftless.loader import load_portfolio

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def plan(
    file: Path,
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Compute buy orders for a portfolio snapshot."""
    portfolio = load_portfolio(file)
    result = compute_plan(portfolio)
    if json_output:
        typer.echo(format_json(result))
    else:
        print_plan(portfolio, result)


@app.command()
def validate(file: Path) -> None:
    """Validate a portfolio file without computing a plan."""
    load_portfolio(file)
    typer.echo("OK")


if __name__ == "__main__":
    app()
