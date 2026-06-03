from driftless.models import BuyOrder, Portfolio, RebalancePlan


def compute_plan(portfolio: Portfolio) -> RebalancePlan:
    positions_by_isin = {p.isin: p for p in portfolio.positions}
    labels = {p.isin: p.label for p in portfolio.positions}
    target_isins = {t.isin for t in portfolio.targets}

    total = sum(p.value_pln for p in portfolio.positions) + portfolio.cash_pln
    warnings: list[str] = []

    for isin in positions_by_isin:
        if isin not in target_isins:
            warnings.append(f"Position {isin} not in target allocation")

    buy_raw: dict[str, float] = {}
    orders_data: list[dict] = []

    for target in portfolio.targets:
        current = positions_by_isin.get(target.isin)
        current_pln = current.value_pln if current else 0.0
        target_pln = total * target.weight
        gap = target_pln - current_pln
        buy_raw[target.isin] = max(0.0, gap)
        orders_data.append(
            {
                "isin": target.isin,
                "label": labels.get(target.isin),
                "current_pln": current_pln,
                "target_pln": target_pln,
                "current_weight": current_pln / total,
                "target_weight": target.weight,
                "drift_pp": (target.weight - current_pln / total) * 100,
            }
        )

    buy_sum = sum(buy_raw.values())
    cash = portfolio.cash_pln
    scale = (cash / buy_sum) if buy_sum > cash and buy_sum > 0 else 1.0
    if scale < 1.0:
        warnings.append(
            f"Buy orders scaled down to fit available cash ({cash:,.2f} PLN)"
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
            buy_pln=buy_raw[d["isin"]] * scale,
        )
        for d in orders_data
    )

    deployed = sum(o.buy_pln for o in orders)
    return RebalancePlan(
        total_pln=total,
        positions_pln=sum(p.value_pln for p in portfolio.positions),
        cash_pln=cash,
        orders=orders,
        cash_deployed=deployed,
        leftover_cash=cash - deployed,
        warnings=tuple(warnings),
    )
