import math
from dataclasses import dataclass

from driftless.models import BuyOrder, Portfolio, RebalancePlan

# Gaps/cash differences below one grosz are float noise, not real constraints.
_EPSILON_PLN = 0.005


@dataclass(frozen=True)
class _Leg:
    isin: str
    label: str | None
    current_pln: float
    target_weight: float
    target_pln: float

    @property
    def gap(self) -> float:
        return self.target_pln - self.current_pln


def _water_level(gaps: list[float], cash: float) -> float:
    """Level L such that sum(max(0, gap - L)) == cash (exact water-filling).

    Spending ``cash`` on the largest gaps first leaves every funded position
    with the same remaining shortfall L, which minimizes both the largest
    remaining gap and the sum of squared remaining gaps.
    """
    ordered = sorted(gaps, reverse=True)
    running = 0.0
    for count, gap in enumerate(ordered, start=1):
        running += gap
        level = (running - cash) / count
        next_gap = ordered[count] if count < len(ordered) else 0.0
        if level >= next_gap:
            return max(level, 0.0)
    return 0.0


def _allocate_cash_to_minimize_drift(gaps: dict[str, float], cash: float) -> dict[str, float]:
    positive = [gap for gap in gaps.values() if gap > 0]
    if cash <= 0 or not positive:
        return {isin: 0.0 for isin in gaps}
    level = _water_level(positive, cash)
    return {isin: max(0.0, gap - level) for isin, gap in gaps.items()}


def _round_to_grosz(amounts: dict[str, float], cash: float) -> dict[str, float]:
    """Round to 0.01 PLN (largest remainder) without ever exceeding ``cash``."""
    cash_grosze = math.floor(cash * 100 + 1e-9)
    raw = {isin: amount * 100 for isin, amount in amounts.items()}
    floors = {isin: math.floor(value + 1e-9) for isin, value in raw.items()}
    budget = min(round(sum(raw.values())), cash_grosze) - sum(floors.values())
    by_remainder = sorted(raw, key=lambda isin: raw[isin] - floors[isin], reverse=True)
    for isin in by_remainder[: max(0, budget)]:
        floors[isin] += 1
    return {isin: grosze / 100 for isin, grosze in floors.items()}


def compute_plan(portfolio: Portfolio) -> RebalancePlan:
    positions_by_isin = {p.isin: p for p in portfolio.positions}
    target_isins = {t.isin for t in portfolio.targets}

    positions_total = sum(p.value_pln for p in portfolio.positions)
    total = positions_total + portfolio.cash_pln
    warnings: list[str] = []

    legs = [
        _Leg(
            isin=t.isin,
            label=positions_by_isin[t.isin].label if t.isin in positions_by_isin else None,
            current_pln=positions_by_isin[t.isin].value_pln if t.isin in positions_by_isin else 0.0,
            target_weight=t.weight,
            target_pln=total * t.weight,
        )
        for t in portfolio.targets
    ]
    # Held positions outside the target stay visible (target 0%, never sold or bought).
    for position in portfolio.positions:
        if position.isin not in target_isins:
            warnings.append(f"Position {position.isin} not in target allocation")
            legs.append(_Leg(position.isin, position.label, position.value_pln, 0.0, 0.0))

    cash = portfolio.cash_pln
    gaps = {leg.isin: max(0.0, leg.gap) for leg in legs}
    if sum(gaps.values()) - cash > _EPSILON_PLN:
        warnings.append(f"Buy orders constrained to available cash ({cash:,.2f} PLN)")

    buys = _round_to_grosz(_allocate_cash_to_minimize_drift(gaps, cash), cash)

    deployed = sum(buys.values())
    invested_after = positions_total + deployed
    orders = []
    for leg in legs:
        buy = buys[leg.isin]
        current_weight = leg.current_pln / positions_total if positions_total > 0 else 0.0
        after_weight = (leg.current_pln + buy) / invested_after if invested_after > 0 else 0.0
        orders.append(
            BuyOrder(
                isin=leg.isin,
                label=leg.label,
                current_pln=leg.current_pln,
                target_pln=leg.target_pln,
                current_weight=current_weight,
                target_weight=leg.target_weight,
                drift_pp=(leg.target_weight - current_weight) * 100,
                buy_pln=buy,
                after_weight=after_weight,
                drift_after_pp=(leg.target_weight - after_weight) * 100,
            )
        )

    return RebalancePlan(
        total_pln=total,
        positions_pln=positions_total,
        cash_pln=cash,
        orders=tuple(orders),
        cash_deployed=deployed,
        leftover_cash=max(0.0, cash - deployed),
        warnings=tuple(warnings),
    )
