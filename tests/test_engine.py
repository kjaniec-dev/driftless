import random

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


def _four_etf_portfolio(cash: float = 500.0) -> Portfolio:
    return Portfolio(
        base_currency="PLN",
        cash_pln=cash,
        positions=(
            Position("IE00B5BMR087", 3400, "SXR8"),
            Position("IE0006WW1TQ4", 4300, "EXUS"),
            Position("IE00BKM4GZ66", 1200, "IS3N"),
            Position("IE00B4ND3602", 1100, "EGLN"),
        ),
        targets=(
            Target("IE00B5BMR087", 0.30),
            Target("IE0006WW1TQ4", 0.40),
            Target("IE00BKM4GZ66", 0.15),
            Target("IE00B4ND3602", 0.15),
        ),
    )


def _by_label(plan):
    return {o.label: o for o in plan.orders}


def test_basic_buy_plan():
    plan = compute_plan(_portfolio())
    assert plan.total_pln == 80000
    by_isin = {o.isin: o for o in plan.orders}
    assert by_isin["IE00BK5BQT80"].buy_pln == 3000
    assert by_isin["IE00B4L5Y983"].buy_pln == 2000
    assert plan.leftover_cash == 0
    assert plan.warnings == ()


def test_current_weights_are_based_on_invested_positions():
    plan = compute_plan(_four_etf_portfolio())

    by_label = _by_label(plan)
    assert sum(o.current_weight for o in plan.orders) == pytest.approx(1.0)
    assert by_label["SXR8"].current_weight == pytest.approx(0.34)
    assert by_label["EXUS"].current_weight == pytest.approx(0.43)
    assert by_label["IS3N"].current_weight == pytest.approx(0.12)
    assert by_label["EGLN"].current_weight == pytest.approx(0.11)
    assert by_label["SXR8"].drift_pp == pytest.approx(-4.0)
    assert by_label["EXUS"].drift_pp == pytest.approx(-3.0)
    assert by_label["IS3N"].drift_pp == pytest.approx(3.0)
    assert by_label["EGLN"].drift_pp == pytest.approx(4.0)


def test_cash_minimizes_remaining_underweight_drift():
    plan = compute_plan(_four_etf_portfolio())

    by_label = _by_label(plan)
    assert by_label["SXR8"].buy_pln == 0
    assert by_label["EXUS"].buy_pln == 0
    assert by_label["IS3N"].buy_pln == pytest.approx(200)
    assert by_label["EGLN"].buy_pln == pytest.approx(300)
    assert plan.cash_deployed == pytest.approx(500)
    assert plan.leftover_cash == pytest.approx(0)
    assert "constrained" in plan.warnings[0]


def test_drift_after_buy_is_reported_on_the_post_purchase_portfolio():
    plan = compute_plan(_four_etf_portfolio())

    by_label = _by_label(plan)
    # invested after buy = 10_000 + 500 = 10_500
    assert sum(o.after_weight for o in plan.orders) == pytest.approx(1.0)
    assert by_label["IS3N"].after_weight == pytest.approx(1400 / 10500)
    assert by_label["EGLN"].after_weight == pytest.approx(1400 / 10500)
    # funded legs end up with the same remaining shortfall (water-filling)
    assert by_label["IS3N"].drift_after_pp == pytest.approx(by_label["EGLN"].drift_after_pp)


def test_deploys_all_cash_when_cash_limits_rebalance():
    plan = compute_plan(_portfolio(cash=2500))
    assert sum(o.buy_pln for o in plan.orders) == pytest.approx(2500)


def test_no_constraint_warning_when_cash_equals_total_gap_up_to_float_noise():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=3333.33,
        positions=(
            Position("IE00BK5BQT80", 1000.1),
            Position("IE00B4L5Y983", 2000.2),
        ),
        targets=(Target("IE00BK5BQT80", 1 / 3), Target("IE00B4L5Y983", 2 / 3)),
    )
    assert compute_plan(portfolio).warnings == ()


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


def test_only_cash_buys_by_target_weight():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=1000,
        positions=(),
        targets=(Target("IE00BK5BQT80", 0.7), Target("IE00B4L5Y983", 0.3)),
    )
    plan = compute_plan(portfolio)
    by_isin = {o.isin: o for o in plan.orders}
    assert by_isin["IE00BK5BQT80"].buy_pln == pytest.approx(700)
    assert by_isin["IE00B4L5Y983"].buy_pln == pytest.approx(300)
    assert all(o.current_weight == 0 for o in plan.orders)
    assert by_isin["IE00BK5BQT80"].after_weight == pytest.approx(0.7)


def test_position_outside_target_is_listed_and_never_traded():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=1000,
        positions=(
            Position("IE00BK5BQT80", 5000, "VWCE"),
            Position("IE00B4L5Y983", 3000, "IWDA"),
            Position("IE00B5BMR087", 2000, "SXR8"),
        ),
        targets=(Target("IE00BK5BQT80", 0.5), Target("IE00B4L5Y983", 0.5)),
    )
    plan = compute_plan(portfolio)

    assert any("IE00B5BMR087" in w for w in plan.warnings)
    by_label = _by_label(plan)
    assert by_label["SXR8"].target_weight == 0
    assert by_label["SXR8"].buy_pln == 0
    assert by_label["VWCE"].buy_pln == 0
    assert by_label["IWDA"].buy_pln == pytest.approx(1000)
    assert sum(o.current_weight for o in plan.orders) == pytest.approx(1.0)


def test_buys_are_rounded_to_grosze_without_exceeding_cash():
    portfolio = Portfolio(
        base_currency="PLN",
        cash_pln=100,
        positions=(
            Position("IE00BK5BQT80", 0),
            Position("IE00B4L5Y983", 0),
            Position("IE00B5BMR087", 0),
        ),
        targets=(
            Target("IE00BK5BQT80", 1 / 3),
            Target("IE00B4L5Y983", 1 / 3),
            Target("IE00B5BMR087", 1 / 3),
        ),
    )
    plan = compute_plan(portfolio)

    assert all(round(o.buy_pln * 100) == pytest.approx(o.buy_pln * 100) for o in plan.orders)
    assert plan.cash_deployed == pytest.approx(100)
    assert plan.cash_deployed <= 100
    assert plan.leftover_cash >= 0


def test_random_portfolios_respect_buy_only_invariants():
    rng = random.Random(1)
    for _ in range(500):
        k = rng.randint(1, 6)
        isins = [f"IE00B5BMR0{i:02d}" for i in range(k)]
        raw_weights = [rng.random() + 0.01 for _ in range(k)]
        norm = sum(raw_weights)
        cash = round(rng.uniform(0, 3000), 2)
        portfolio = Portfolio(
            base_currency="PLN",
            cash_pln=cash,
            positions=tuple(Position(i, round(rng.uniform(0, 5000), 2)) for i in isins),
            targets=tuple(Target(i, w / norm) for i, w in zip(isins, raw_weights)),
        )
        plan = compute_plan(portfolio)

        assert all(o.buy_pln >= 0 for o in plan.orders)
        assert plan.cash_deployed <= cash + 1e-9
        assert plan.leftover_cash >= 0
        gap_sum = sum(max(0.0, o.target_pln - o.current_pln) for o in plan.orders)
        # cash is fully used whenever there is enough underweight to absorb it
        assert plan.cash_deployed == pytest.approx(min(cash, gap_sum), abs=0.011)
        # never buy past target
        for o in plan.orders:
            assert o.buy_pln <= max(0.0, o.target_pln - o.current_pln) + 0.011
        # funded legs share one remaining shortfall
        remaining = [
            o.target_pln - o.current_pln - o.buy_pln for o in plan.orders if o.buy_pln > 0.02
        ]
        if remaining and plan.cash_deployed < gap_sum - 0.05:
            assert max(remaining) - min(remaining) < 0.02
