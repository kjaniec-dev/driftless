from rich.console import Console
from rich.table import Table

from driftless.models import Portfolio, RebalancePlan


def print_plan(portfolio: Portfolio, plan: RebalancePlan) -> None:
    console = Console()
    as_of = portfolio.as_of or "—"
    console.print(f"\n[bold]Driftless[/bold] — plan as of {as_of}")
    console.print(
        f"Total portfolio: {plan.total_pln:,.0f} PLN  "
        f"(positions: {plan.positions_pln:,.0f} + cash: {plan.cash_pln:,.0f})\n"
    )

    for warning in plan.warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    table = Table(show_header=True, header_style="bold")
    table.add_column("ISIN")
    table.add_column("Label")
    table.add_column("Current", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Drift", justify="right")
    table.add_column("Buy (PLN)", justify="right")

    for order in plan.orders:
        label = order.label or ""
        drift = f"{order.drift_pp:+.2f}pp"
        table.add_row(
            order.isin,
            label,
            f"{order.current_weight * 100:.2f}%",
            f"{order.target_weight * 100:.2f}%",
            drift,
            f"{order.buy_pln:,.2f}",
        )

    console.print(table)
    console.print(f"\nCash deployed: {plan.cash_deployed:,.2f} PLN")
    console.print(f"Leftover cash: {plan.leftover_cash:,.2f} PLN\n")
