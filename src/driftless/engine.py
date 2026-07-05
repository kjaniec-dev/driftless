from driftless.models import BuyOrder, Portfolio, RebalancePlan


def _allocate_cash_to_minimize_drift(
    buy_raw: dict[str, float], cash: float
) -> dict[str, float]:
    positive_gaps = [gap for gap in buy_raw.values() if gap > 0]
    if cash <= 0 or not positive_gaps:
        return {isin: 0.0 for isin in buy_raw}

    total_gap = sum(positive_gaps)
    if cash >= total_gap:
        return dict(buy_raw)

    low = 0.0
    high = max(positive_gaps)
    for _ in range(60):
        level = (low + high) / 2
        deployed = sum(max(0.0, gap - level) for gap in positive_gaps)
        if deployed > cash:
            low = level
        else:
            high = level

    return {isin: max(0.0, gap - high) for isin, gap in buy_raw.items()}


def compute_plan(portfolio: Portfolio) -> RebalancePlan:
    positions_by_isin = {p.isin: p for p in portfolio.positions}
    labels = {p.isin: p.label for p in portfolio.positions}
    target_isins = {t.isin for t in portfolio.targets}

    positions_total = sum(p.value_pln for p in portfolio.positions)
    total = positions_total + portfolio.cash_pln
    warnings: list[str] = []

    for isin in positions_by_isin:
        if isin not in target_isins:
            warnings.append(f"Position {isin} not in target allocation")

    buy_raw: dict[str, float] = {}
    orders_data: list[dict] = []

    for target in portfolio.targets:
        current = positions_by_isin.get(target.isin)
        current_pln = current.value_pln if current else 0.0
        current_weight = current_pln / positions_total if positions_total > 0 else 0.0
        target_pln = total * target.weight
        gap = target_pln - current_pln
        buy_raw[target.isin] = max(0.0, gap)
        orders_data.append(
            {
                "isin": target.isin,
                "label": labels.get(target.isin),
                "current_pln": current_pln,
                "target_pln": target_pln,
                "current_weight": current_weight,
                "target_weight": target.weight,
                "drift_pp": (target.weight - current_weight) * 100,
            }
        )

    cash = portfolio.cash_pln
    buys = _allocate_cash_to_minimize_drift(buy_raw, cash)
    if sum(buy_raw.values()) > cash:
        warnings.append(
            f"Buy orders constrained to available cash ({cash:,.2f} PLN)"
        )

    orders = tuple(
        BuyOrder(
            isin=d["isin"],
            label=d["label"],
            current_pln=d["current_pln"],
            target_pln=d["target_pln"],
            current_weight=d["current_weight"],
            target_weight=d["target_weight"],
            drift_pp=d["drift_pp"],
            buy_pln=buys[d["isin"]],
        )
        for d in orders_data
    )

    deployed = sum(o.buy_pln for o in orders)
    deployed = min(deployed, cash)
    leftover = cash - deployed
    if abs(leftover) < 1e-6:
        leftover = 0.0

    return RebalancePlan(
        total_pln=total,
        positions_pln=positions_total,
        cash_pln=cash,
        orders=orders,
        cash_deployed=deployed,
        leftover_cash=leftover,
        warnings=tuple(warnings),
    )
