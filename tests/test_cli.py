from pathlib import Path

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
