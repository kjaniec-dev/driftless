from dataclasses import replace
from pathlib import Path

import typer

from driftless.engine import compute_plan
from driftless.errors import PortfolioFileError, PortfolioValidationError
from driftless.formatters.json_out import format_json
from driftless.formatters.table import print_plan
from driftless.loader import load_portfolio
from driftless.models import Portfolio
from driftless.nbp import fetch_nbp_rate

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
    deploy: float | None = typer.Option(
        None, "--deploy", "-d", help="Override available cash to deploy (PLN)"
    ),
) -> None:
    """Compute buy orders for a portfolio snapshot."""
    portfolio = _load_or_exit(file)
    if deploy is not None:
        if deploy < 0:
            typer.echo("Error: Overridden cash to deploy must be non-negative", err=True)
            raise typer.Exit(EXIT_USAGE)
        portfolio = replace(portfolio, cash_pln=deploy)
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


@app.command()
def fx(
    currencies: list[str] = typer.Argument(
        None, help="Currencies to fetch (e.g., EUR USD). Defaults to EUR, USD, CHF, GBP."
    )
) -> None:
    """Fetch official exchange rates from the Narodowy Bank Polski (NBP)."""
    targets = currencies or ["EUR", "USD", "CHF", "GBP"]
    typer.echo("NBP Exchange Rates (Table A mid):")
    for currency in targets:
        currency = currency.upper()
        if currency == "PLN":
            typer.echo("  PLN: 1.0000 (Base)")
            continue
        try:
            rate = fetch_nbp_rate(currency)
            typer.echo(f"  {currency}: {rate:.4f} PLN")
        except Exception as exc:
            typer.echo(f"  {currency}: Error ({exc})", err=True)
            raise typer.Exit(EXIT_VALIDATION)


if __name__ == "__main__":
    app()
