# Driftless Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that reads a JSON portfolio snapshot (ISIN + PLN values + target weights) and outputs concrete buy orders for buy-only ETF rebalancing.

**Architecture:** Pure-function core (`engine.py`) separated from JSON I/O (`loader.py`) and CLI formatting. Input validated via JSON Schema + business rules. No network, no broker integration in v1.

**Tech Stack:** Python 3.14+, typer, jsonschema, rich, pytest, hatchling (pyproject.toml)

**Spec:** `docs/superpowers/specs/2026-06-03-driftless-design.md`

**Project path:** `/Users/kjaniec-dev/dev/projects/driftless`

---

## File Map

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, `[project.scripts] driftless = driftless.cli:app` |
| `src/driftless/models.py` | `Position`, `Target`, `Portfolio`, `BuyOrder`, `RebalancePlan` |
| `src/driftless/loader.py` | Load JSON file → `Portfolio` |
| `src/driftless/validate.py` | Weight sum, duplicate ISIN, empty portfolio |
| `src/driftless/engine.py` | Buy-only algorithm with cash scaling |
| `src/driftless/formatters/table.py` | Human-readable output via `rich` |
| `src/driftless/formatters/json_out.py` | `--json` output |
| `src/driftless/cli.py` | `plan` and `validate` commands |
| `schemas/portfolio.schema.json` | Structural JSON Schema |
| `examples/portfolio.example.json` | Documented example |
| `tests/test_engine.py` | Core algorithm tests |
| `tests/test_loader.py` | Validation tests |
| `tests/fixtures/sample_portfolio.json` | Test fixture |

---

## Chunk 1: Project Scaffold

### Task 1: Initialize Python package

**Files:**
- Create: `pyproject.toml`
- Create: `src/driftless/__init__.py`
- Create: `src/driftless/__main__.py`
- Create: `README.md`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "driftless"
version = "0.1.0"
description = "Buy-only UCITS portfolio drift fixer — concrete PLN buy orders from a JSON snapshot"
readme = "README.md"
requires-python = ">=3.14"
license = { text = "MIT" }
dependencies = [
  "typer>=0.12",
  "jsonschema>=4.21",
  "rich>=13.7",
]

[project.scripts]
driftless = "driftless.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/driftless"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[dependency-groups]
dev = ["pytest>=8.0"]
```

- [ ] **Step 2: Create package stubs**

`src/driftless/__init__.py`:
```python
__version__ = "0.1.0"
```

`src/driftless/__main__.py`:
```python
from driftless.cli import app

app()
```

- [ ] **Step 3: Install editable**

Run: `cd /Users/kjaniec-dev/dev/projects/driftless && pip install -e ".[dev]"`
Expected: Successfully installed driftless

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/driftless/__init__.py src/driftless/__main__.py README.md
git commit -m "chore: scaffold driftless package"
```

---

## Chunk 2: Domain Models

### Task 2: Dataclasses

**Files:**
- Create: `src/driftless/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write models**

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Position:
    isin: str
    value_pln: float
    label: str | None = None


@dataclass(frozen=True)
class Target:
    isin: str
    weight: float


@dataclass(frozen=True)
class Portfolio:
    base_currency: str
    cash_pln: float
    positions: tuple[Position, ...]
    targets: tuple[Target, ...]
    as_of: str | None = None


@dataclass(frozen=True)
class BuyOrder:
    isin: str
    label: str | None
    current_pln: float
    target_pln: float
    current_weight: float
    target_weight: float
    drift_pp: float
    buy_pln: float


@dataclass(frozen=True)
class RebalancePlan:
    total_pln: float
    positions_pln: float
    cash_pln: float
    orders: tuple[BuyOrder, ...]
    cash_deployed: float
    leftover_cash: float
    warnings: tuple[str, ...] = field(default_factory=tuple)
```

- [ ] **Step 2: Commit**

```bash
git add src/driftless/models.py
git commit -m "feat: add portfolio domain models"
```

---

## Chunk 3: JSON Schema + Loader

### Task 3: Schema and loader

**Files:**
- Create: `schemas/portfolio.schema.json`
- Create: `src/driftless/loader.py`
- Create: `src/driftless/validate.py`
- Create: `tests/fixtures/sample_portfolio.json`
- Test: `tests/test_loader.py`

- [ ] **Step 1: Write JSON Schema**

`schemas/portfolio.schema.json` — enforce:
- required: `base_currency`, `cash_pln`, `positions`, `target`
- `base_currency` enum `["PLN"]`
- `positions[].isin` pattern `^[A-Z]{2}[A-Z0-9]{9}[0-9]$`
- numeric minimums 0

- [ ] **Step 2: Write failing loader test**

```python
from pathlib import Path
import pytest
from driftless.loader import load_portfolio


FIXTURE = Path(__file__).parent / "fixtures" / "sample_portfolio.json"


def test_load_valid_portfolio():
    p = load_portfolio(FIXTURE)
    assert p.base_currency == "PLN"
    assert len(p.positions) == 2
    assert len(p.targets) == 2


def test_rejects_weights_not_summing_to_one(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text('{"base_currency":"PLN","cash_pln":0,"positions":[],"target":[{"isin":"IE00BK5BQT80","weight":0.5}]}')
    with pytest.raises(ValueError, match="weight"):
        load_portfolio(bad)
```

- [ ] **Step 3: Run test — expect FAIL**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL — `load_portfolio` not defined

- [ ] **Step 4: Implement loader + validate**

`loader.py`:
```python
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
```

`validate.py`:
```python
from driftless.models import Portfolio


def validate_portfolio(p: Portfolio) -> None:
    if abs(sum(t.weight for t in p.targets) - 1.0) > 1e-4:
        raise ValueError("Target weights must sum to 1.0")

    isins = [pos.isin for pos in p.positions]
    if len(isins) != len(set(isins)):
        raise ValueError("Duplicate ISIN in positions")

    target_isins = [t.isin for t in p.targets]
    if len(target_isins) != len(set(target_isins)):
        raise ValueError("Duplicate ISIN in target")

    total = sum(pos.value_pln for pos in p.positions) + p.cash_pln
    if total <= 0:
        raise ValueError("Portfolio total must be positive")
```

- [ ] **Step 5: Add fixture**

Copy example from design spec into `tests/fixtures/sample_portfolio.json`.

- [ ] **Step 6: Run tests — expect PASS**

Run: `pytest tests/test_loader.py -v`

- [ ] **Step 7: Commit**

```bash
git add schemas/ src/driftless/loader.py src/driftless/validate.py tests/
git commit -m "feat: add JSON schema and portfolio loader"
```

---

## Chunk 4: Rebalance Engine

### Task 4: Core algorithm

**Files:**
- Create: `src/driftless/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write failing engine tests**

```python
import pytest
from driftless.models import Portfolio, Position, Target
from driftless.engine import compute_plan


def _portfolio(cash=5000.0):
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


def test_all_overweight_no_buys():
    p = Portfolio(
        base_currency="PLN",
        cash_pln=1000,
        positions=(Position("IE00BK5BQT80", 90000, "VWCE"),),
        targets=(Target("IE00BK5BQT80", 0.50), Target("IE00B4L5Y983", 0.50)),
    )
    plan = compute_plan(p)
    assert plan.cash_deployed == 0
    assert plan.leftover_cash == 1000
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/test_engine.py -v`

- [ ] **Step 3: Implement engine.py**

(Same algorithm as spec — `from driftless.models import BuyOrder, Portfolio, RebalancePlan`.)

- [ ] **Step 4: Run — expect PASS**

Run: `pytest tests/test_engine.py -v`

- [ ] **Step 5: Commit**

```bash
git add src/driftless/engine.py tests/test_engine.py
git commit -m "feat: implement buy-only rebalance engine"
```

---

## Chunk 5: CLI + Formatters

### Task 5: Wire CLI

**Files:**
- Create: `src/driftless/formatters/table.py`
- Create: `src/driftless/formatters/json_out.py`
- Create: `src/driftless/cli.py`

- [ ] **Step 1: Implement formatters** (`json_out` imports `from driftless.models import RebalancePlan`)

- [ ] **Step 2: Implement cli.py** (`from driftless.loader import load_portfolio`, etc.)

- [ ] **Step 3: Manual smoke test**

Run: `driftless plan examples/portfolio.example.json`
Expected: table with VWCE 3000 / IWDA 2000

Run: `driftless validate examples/portfolio.example.json`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/driftless/cli.py src/driftless/formatters/
git commit -m "feat: add CLI with plan and validate commands"
```

---

## Chunk 6: README

- [ ] **Step 1: Write README** (project name Driftless, Python 3.14, `driftless plan` examples)

- [ ] **Step 2: Run full test suite** — `pytest -v`

- [ ] **Step 3: Commit** — `docs: add README with usage and disclaimer`

---

## Verification Checklist

- [ ] `pytest` green
- [ ] `driftless plan examples/portfolio.example.json` matches design spec output
- [ ] Invalid weights rejected with clear error
- [ ] `--json` output parseable
- [ ] No network dependencies

---

## Execution Handoff

Plan saved. Implement with `@superpowers:executing-plans` or `@superpowers:subagent-driven-development`.

Estimated effort: **~2–3 hours** for v1.
