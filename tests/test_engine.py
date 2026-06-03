import pytest

from driftless.engine import compute_plan
from driftless.models import Portfolio, Position, Target


def _portfolio(cash: float = 5000.0) -> Portfolio:
    return Portfolio(
        base_currency="PLN",
        cash_pln=cash,
        positions=(
            Position("IE00BK5BQT80", 45000, "VWCE"),
            Position("IE00B4L5Y983", 30000, "IWDA"),
        ),
        targets=(
            Target("IE00BK5BQT80", 0.60),
            Target("IE00B4L5Y983", 0.40),
        ),
    )


def test_basic_buy_plan():
    plan = compute_plan(_portfolio())
    assert plan.total_pln == 80000
    by_isin = {o.isin: o for o in plan.orders}
    assert by_isin["IE00BK5BQT80"].buy_pln == 3000
    assert by_isin["IE00B4L5Y983"].buy_pln == 2000
    assert plan.leftover_cash == 0


def test_scales_down_when_cash_insufficient():
    plan = compute_plan(_portfolio(cash=2500))
    assert sum(o.buy_pln for o in plan.orders) == pytest.approx(2500)


def test_deploys_cash_to_missing_target_leg():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=1000,
        positions=(Position("IE00BK5BQT80", 90000, "VWCE"),),
        targets=(
            Target("IE00BK5BQT80", 0.50),
            Target("IE00B4L5Y983", 0.50),
        ),
    )
    plan = compute_plan(portfolio)
    by_isin = {o.isin: o for o in plan.orders}
    assert by_isin["IE00BK5BQT80"].buy_pln == 0
    assert by_isin["IE00B4L5Y983"].buy_pln == pytest.approx(1000)
    assert plan.leftover_cash == pytest.approx(0)


def test_single_asset_at_target_no_buys():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=0,
        positions=(Position("IE00BK5BQT80", 100000, "VWCE"),),
        targets=(Target("IE00BK5BQT80", 1.0),),
    )
    plan = compute_plan(portfolio)
    assert plan.cash_deployed == 0
    assert plan.leftover_cash == 0
