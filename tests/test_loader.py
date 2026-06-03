from pathlib import Path

import pytest

from driftless.loader import load_portfolio

FIXTURE = Path(__file__).parent / "fixtures" / "sample_portfolio.json"


def test_load_valid_portfolio():
    portfolio = load_portfolio(FIXTURE)
    assert portfolio.base_currency == "PLN"
    assert len(portfolio.positions) == 2
    assert len(portfolio.targets) == 2


def test_rejects_weights_not_summing_to_one(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"base_currency":"PLN","cash_pln":0,"positions":[],"target":[{"isin":"IE00BK5BQT80","weight":0.5}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="weight"):
        load_portfolio(bad)
