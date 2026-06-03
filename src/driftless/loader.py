import json
from importlib.resources import files
from pathlib import Path

import jsonschema

from driftless.errors import PortfolioFileError, PortfolioValidationError
from driftless.models import Portfolio, Position, Target
from driftless.nbp import fetch_nbp_rate
from driftless.validate import validate_portfolio


def _load_schema() -> dict:
    resource = files("driftless").joinpath("schemas/portfolio.schema.json")
    return json.loads(resource.read_text(encoding="utf-8"))


def _resolve_value_pln(p: dict) -> float:
    if "value_pln" in p:
        return float(p["value_pln"])

    val = float(p["value"])
    curr = p["currency"].upper()
    if curr == "PLN":
        return val

    try:
        rate = fetch_nbp_rate(curr)
        return val * rate
    except Exception as exc:
        raise ValueError(f"Could not convert {val} {curr} to PLN: {exc}")


def load_portfolio(path: Path | str) -> Portfolio:
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise PortfolioFileError(f"Portfolio file not found: {path}")
    except OSError as exc:
        raise PortfolioFileError(f"Cannot read portfolio file {path}: {exc}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PortfolioValidationError(f"Invalid JSON in {path}: {exc}")

    schema = _load_schema()
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path) or "(root)"
        raise PortfolioValidationError(f"Schema error at {location}: {exc.message}")

    try:
        positions_tuple = tuple(
            Position(
                isin=p["isin"],
                value_pln=_resolve_value_pln(p),
                label=p.get("label"),
            )
            for p in data["positions"]
        )
    except ValueError as exc:
        raise PortfolioValidationError(str(exc))

    portfolio = Portfolio(
        base_currency=data["base_currency"],
        cash_pln=float(data["cash_pln"]),
        positions=positions_tuple,
        targets=tuple(
            Target(isin=t["isin"], weight=float(t["weight"]))
            for t in data["target"]
        ),
        as_of=data.get("as_of"),
    )

    try:
        validate_portfolio(portfolio)
    except ValueError as exc:
        raise PortfolioValidationError(str(exc))

    return portfolio
