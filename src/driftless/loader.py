import json
from pathlib import Path

import jsonschema

from driftless.models import Portfolio, Position, Target
from driftless.validate import validate_portfolio

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "portfolio.schema.json"


def load_portfolio(path: Path | str) -> Portfolio:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)

    portfolio = Portfolio(
        base_currency=data["base_currency"],
        cash_pln=float(data["cash_pln"]),
        positions=tuple(
            Position(
                isin=p["isin"],
                value_pln=float(p["value_pln"]),
                label=p.get("label"),
            )
            for p in data["positions"]
        ),
        targets=tuple(
            Target(isin=t["isin"], weight=float(t["weight"]))
            for t in data["target"]
        ),
        as_of=data.get("as_of"),
    )
    validate_portfolio(portfolio)
    return portfolio
