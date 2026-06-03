from driftless.models import Portfolio


def validate_portfolio(portfolio: Portfolio) -> None:
    if abs(sum(t.weight for t in portfolio.targets) - 1.0) > 1e-4:
        raise ValueError("Target weights must sum to 1.0")

    position_isins = [pos.isin for pos in portfolio.positions]
    if len(position_isins) != len(set(position_isins)):
        raise ValueError("Duplicate ISIN in positions")

    target_isins = [t.isin for t in portfolio.targets]
    if len(target_isins) != len(set(target_isins)):
        raise ValueError("Duplicate ISIN in target")

    total = sum(pos.value_pln for pos in portfolio.positions) + portfolio.cash_pln
    if total <= 0:
        raise ValueError("Portfolio total must be positive")
