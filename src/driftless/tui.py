from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from driftless.engine import compute_plan
from driftless.errors import PortfolioFileError, PortfolioValidationError
from driftless.loader import load_portfolio
from driftless.models import Portfolio, RebalancePlan


class DriftlessApp(App[None]):
    """Interactive TUI for the Driftless portfolio rebalancer."""

    TITLE = "Driftless"
    SUB_TITLE = "Buy-only UCITS portfolio rebalancer"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+r", "compute", "Recompute"),
    ]

    CSS = """
    #controls {
        height: auto;
        padding: 1 2;
        border-bottom: solid $panel;
    }

    .control-row {
        height: 3;
        margin-bottom: 1;
    }

    .field-label {
        width: 22;
        content-align: left middle;
        color: $text-muted;
    }

    #file-input {
        width: 1fr;
    }

    #cash-input {
        width: 24;
    }

    #compute-btn {
        margin-left: 1;
        min-width: 10;
    }

    #results {
        padding: 1 2;
    }

    #summary {
        height: auto;
        margin-bottom: 1;
    }

    #warnings {
        height: auto;
        margin-bottom: 1;
    }

    #plan-table {
        height: auto;
        margin-bottom: 1;
    }

    #cash-footer {
        height: auto;
    }
    """

    def __init__(self, initial_file: str = "") -> None:
        super().__init__()
        self._initial_file = initial_file

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="controls"):
            with Horizontal(classes="control-row"):
                yield Label("Portfolio file:", classes="field-label")
                yield Input(
                    value=self._initial_file,
                    placeholder="path/to/portfolio.json",
                    id="file-input",
                )
                yield Button("Compute", id="compute-btn", variant="primary")
            with Horizontal(classes="control-row"):
                yield Label("Cash override (PLN):", classes="field-label")
                yield Input(
                    placeholder="optional — overrides file value",
                    id="cash-input",
                )
        with ScrollableContainer(id="results"):
            yield Static("", id="summary")
            yield Static("", id="warnings")
            yield DataTable(id="plan-table")
            yield Static("", id="cash-footer")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("ISIN", "Label", "Current", "Target", "Drift", "Buy (PLN)")
        if self._initial_file:
            self._do_compute()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "compute-btn":
            self._do_compute()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_compute()

    def action_compute(self) -> None:
        self._do_compute()

    def _do_compute(self) -> None:
        file_str = self.query_one("#file-input", Input).value.strip()
        if not file_str:
            self.notify("Enter a portfolio file path first.", severity="warning")
            return

        cash_str = self.query_one("#cash-input", Input).value.strip()
        cash_override: float | None = None
        if cash_str:
            try:
                cash_override = float(cash_str.replace(",", ""))
                if cash_override < 0:
                    self.notify("Cash override must be non-negative.", severity="error")
                    return
            except ValueError:
                self.notify("Cash override must be a number.", severity="error")
                return

        self._load_and_render(file_str, cash_override)

    @work(thread=True)
    def _load_and_render(self, file_str: str, cash_override: float | None) -> None:
        try:
            portfolio = load_portfolio(Path(file_str))
        except (PortfolioFileError, PortfolioValidationError) as exc:
            self.call_from_thread(self.notify, str(exc), severity="error")
            return

        if cash_override is not None:
            portfolio = replace(portfolio, cash_pln=cash_override)

        plan = compute_plan(portfolio)
        self.call_from_thread(self._update_display, portfolio, plan)

    def _update_display(self, portfolio: Portfolio, plan: RebalancePlan) -> None:
        as_of = portfolio.as_of or "—"
        self.query_one("#summary", Static).update(
            f"[bold]Portfolio:[/bold] {plan.total_pln:,.0f} PLN  "
            f"[dim](positions: {plan.positions_pln:,.0f}  cash: {plan.cash_pln:,.0f}  as of {as_of})[/dim]"
        )

        warnings_text = "\n".join(f"[yellow]⚠ {w}[/yellow]" for w in plan.warnings)
        self.query_one("#warnings", Static).update(warnings_text)

        table = self.query_one(DataTable)
        table.clear()
        for order in plan.orders:
            drift = Text(
                f"{order.drift_pp:+.2f}pp",
                style="green" if order.drift_pp >= 0 else "red",
            )
            table.add_row(
                order.isin,
                order.label or "",
                f"{order.current_weight * 100:.2f}%",
                f"{order.target_weight * 100:.2f}%",
                drift,
                f"{order.buy_pln:,.2f}",
            )

        self.query_one("#cash-footer", Static).update(
            f"Deployed: [bold]{plan.cash_deployed:,.2f} PLN[/bold]  "
            f"Leftover: [bold]{plan.leftover_cash:,.2f} PLN[/bold]"
        )
