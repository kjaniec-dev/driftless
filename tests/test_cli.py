from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from driftless.cli import app

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "sample_portfolio.json"


def test_plan_ok_exit_code():
    result = runner.invoke(app, ["plan", str(FIXTURE)])
    assert result.exit_code == 0
    assert "Driftless" in result.stdout


def test_missing_file_is_usage_error():
    result = runner.invoke(app, ["plan", "does-not-exist.json"])
    assert result.exit_code == 2
    assert "not found" in result.output
    assert "Traceback" not in result.output


def test_invalid_json_is_validation_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["plan", str(bad)])
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output
    assert "Traceback" not in result.output


def test_bad_weights_is_validation_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(
        '{"base_currency":"PLN","cash_pln":1,"positions":[],'
        '"target":[{"isin":"IE00BK5BQT80","weight":0.5}]}',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["plan", str(bad)])
    assert result.exit_code == 1
    assert "weights" in result.output


def test_init_creates_template(tmp_path):
    target = tmp_path / "portfolio.json"
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 0
    assert target.exists()
    # generated template must itself validate structurally
    validate_result = runner.invoke(app, ["validate", str(target)])
    assert validate_result.exit_code == 0


def test_init_refuses_overwrite(tmp_path):
    target = tmp_path / "portfolio.json"
    target.write_text("{}", encoding="utf-8")
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code == 2
    assert "already exists" in result.output


def test_plan_with_deploy_override():
    # deploy 10,000 PLN instead of the default 5,000 PLN in FIXTURE
    result = runner.invoke(app, ["plan", str(FIXTURE), "--deploy", "10000"])
    assert result.exit_code == 0
    assert "Total portfolio: 85,000 PLN" in result.stdout
    assert "Cash deployed: 10,000.00 PLN" in result.stdout


def test_plan_with_invalid_deploy_override():
    result = runner.invoke(app, ["plan", str(FIXTURE), "--deploy", "-100"])
    assert result.exit_code == 2
    assert "non-negative" in result.output


@patch("driftless.loader.fetch_nbp_rate")
def test_plan_with_multi_currency_positions(mock_fetch, tmp_path):
    # Mock NBP rate of 4.30 for EUR
    mock_fetch.return_value = 4.30

    multi = tmp_path / "multi.json"
    multi.write_text(
        '{"base_currency":"PLN","cash_pln":1000,"as_of":"2026-06-03",'
        '"positions":[{"isin":"IE00BK5BQT80","value":1000,"currency":"EUR","label":"VWCE"}],'
        '"target":[{"isin":"IE00BK5BQT80","weight":1.0}]}',
        encoding="utf-8",
    )

    # 1000 EUR * 4.30 = 4300 PLN + 1000 cash = 5300 PLN total portfolio value
    result = runner.invoke(app, ["plan", str(multi)])
    assert result.exit_code == 0
    assert "Total portfolio: 5,300 PLN" in result.stdout
    assert "positions: 4,300" in result.stdout
    mock_fetch.assert_called_once_with("EUR")


@patch("driftless.cli.fetch_nbp_rate")
def test_fx_command(mock_fetch):
    mock_fetch.return_value = 4.25

    result = runner.invoke(app, ["fx", "EUR"])
    assert result.exit_code == 0
    assert "EUR: 4.2500 PLN" in result.output
    mock_fetch.assert_called_once_with("EUR")


@patch("driftless.cli.fetch_nbp_rate")
def test_fx_command_default_list(mock_fetch):
    mock_fetch.side_effect = lambda c: {"EUR": 4.30, "USD": 4.00, "CHF": 4.50, "GBP": 5.10}[c]

    result = runner.invoke(app, ["fx"])
    assert result.exit_code == 0
    assert "EUR: 4.3000 PLN" in result.output
    assert "USD: 4.0000 PLN" in result.output
    assert "CHF: 4.5000 PLN" in result.output
    assert "GBP: 5.1000 PLN" in result.output
