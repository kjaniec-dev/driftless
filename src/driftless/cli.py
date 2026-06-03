from pathlib import Path

import typer

from driftless.engine import compute_plan
from driftless.errors import PortfolioFileError, PortfolioValidationError
from driftless.formatters.json_out import format_json
from driftless.formatters.table import print_plan
from driftless.loader import load_portfolio
from driftless.models import Portfolio

app = typer.Typer(no_args_is_help=True, add_completion=False, pretty_exceptions_enable=False)

EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_USAGE = 2


def _load_or_exit(file: Path) -> Portfolio:
    try:
        return load_portfolio(file)
    except PortfolioFileError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_USAGE)
    except PortfolioValidationError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(EXIT_VALIDATION)


@app.command()
def plan(
    file: Path,
    json_output: bool = typer.Option(False, "--json", help="Emit JSON instead of a table"),
) -> None:
    """Compute buy orders for a portfolio snapshot."""
    portfolio = _load_or_exit(file)
    result = compute_plan(portfolio)
    if json_output:
        typer.echo(format_json(result))
    else:
        print_plan(portfolio, result)


@app.command()
def validate(file: Path) -> None:
    """Validate a portfolio file without computing a plan."""
    _load_or_exit(file)
    typer.echo("OK")


@app.command()
def init(
    file: Path = typer.Argument(Path("portfolio.json"), help="Where to write the template"),
    force: bool = typer.Option(False, "--force", help="Overwrite if the file exists"),
) -> None:
    """Create a starter portfolio.json you can edit by hand."""
    if file.exists() and not force:
        typer.echo(f"Error: {file} already exists (use --force to overwrite)", err=True)
        raise typer.Exit(EXIT_USAGE)

    template = """{
  "base_currency": "PLN",
  "as_of": "2026-01-01",
  "cash_pln": 1000,
  "positions": [
    { "isin": "IE00BK5BQT80", "value_pln": 6000, "label": "VWCE" },
    { "isin": "IE00B4L5Y983", "value_pln": 4000, "label": "IWDA" }
  ],
  "target": [
    { "isin": "IE00BK5BQT80", "weight": 0.60 },
    { "isin": "IE00B4L5Y983", "weight": 0.40 }
  ]
}
"""
    file.write_text(template, encoding="utf-8")
    typer.echo(f"Created {file}. Edit the values, then run: driftless plan {file}")


if __name__ == "__main__":
    app()
