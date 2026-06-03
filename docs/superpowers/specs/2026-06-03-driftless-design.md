# Driftless — Design Spec

**Date:** 2026-06-03  
**Status:** Approved  
**Scope:** v1 — Python CLI, buy-only rebalancing, PLN base currency

---

## 1. Problem Statement

Investor holding a UCITS ETF basket needs to know **how much PLN to buy of each ISIN** after a cash deposit or periodic contribution, given current portfolio values and a target allocation — without selling positions and without tax/accounting logic.

## 2. Goals

| In scope (v1) | Out of scope |
|---|---|
| Read portfolio snapshot from JSON | Broker API / CSV import |
| ISIN + `value_pln` per position | Tax (PIT, FIFO, cost basis) |
| Target weights summing to 1.0 | Sell orders |
| Buy-only rebalance plan | Investment advice |
| PLN as base currency | Multi-account aggregation |
| CLI table + JSON output | Web UI |
| Input validation | Live price fetching |

## 3. User Workflow

1. Open broker app, copy current ETF values (already in PLN or converted mentally).
2. Copy free cash on account.
3. Update `portfolio.json`.
4. Run `driftless plan portfolio.json`.
5. Execute buy orders manually at broker.

## 4. Input Format

Single JSON file — **full snapshot** mode (default and only mode in v1).

```json
{
  "base_currency": "PLN",
  "as_of": "2026-06-03",
  "cash_pln": 5000,
  "positions": [
    {
      "isin": "IE00BK5BQT80",
      "value_pln": 45000,
      "label": "VWCE"
    },
    {
      "isin": "IE00B4L5Y983",
      "value_pln": 30000,
      "label": "IWDA"
    }
  ],
  "target": [
    { "isin": "IE00BK5BQT80", "weight": 0.60 },
    { "isin": "IE00B4L5Y983", "weight": 0.40 }
  ]
}
```

### Field rules

| Field | Required | Notes |
|---|---|---|
| `base_currency` | yes | Must be `"PLN"` in v1 |
| `as_of` | no | ISO date string; audit trail only |
| `cash_pln` | yes | Free cash on account (≥ 0) |
| `positions[].isin` | yes | 12-char ISIN, uppercase |
| `positions[].value_pln` | yes | Current market value in PLN (≥ 0) |
| `positions[].label` | no | Human-readable ticker/name for output |
| `target[].isin` | yes | Must appear in `positions` or be added with `value_pln: 0` |
| `target[].weight` | yes | Decimal; all weights must sum to 1.0 ± 0.0001 |

### FX / PLN awareness (v1)

All values are **pre-converted to PLN** by the user. The tool does not fetch FX rates in v1. The optional `as_of` field documents when values were observed. v1.1 may add NBP rate helper (`driftless fx`).

## 5. Rebalancing Algorithm (Buy-Only)

```
total = sum(position.value_pln) + cash_pln

for each isin in target:
    current[isin] = position.value_pln or 0
    target_value[isin] = total × weight
    gap[isin] = target_value[isin] - current[isin]

buy_raw[isin] = max(0, gap[isin])          # only underweight
buy_sum = sum(buy_raw)

if buy_sum > cash_pln:
    scale = cash_pln / buy_sum
    buy[isin] = buy_raw[isin] × scale       # proportional cap
else:
    buy[isin] = buy_raw[isin]

leftover_cash = cash_pln - sum(buy)
```

### Derived metrics (output)

- `current_weight = current[isin] / total`
- `target_weight = weight`
- `drift_pp = (target_weight - current_weight) × 100`

### Edge cases

| Case | Behavior |
|---|---|
| Weights ≠ 1.0 | Validation error |
| Duplicate ISIN | Validation error |
| Target ISIN missing from positions | Treat as `value_pln = 0` |
| Position ISIN not in target | Warning; excluded from buys |
| All assets overweight | No buys; warn leftover cash |
| `buy_sum > cash_pln` | Scale down; note in output |
| `buy_sum < cash_pln` | Report leftover cash |
| Zero total (empty portfolio + zero cash) | Validation error |

## 6. CLI Interface

```
driftless plan <file>          # compute and print buy plan
driftless validate <file>      # schema + business rules only
driftless plan <file> --json   # machine-readable output
```

### Example output (table)

```
Driftless — plan as of 2026-06-03
Total portfolio: 80,000 PLN  (positions: 75,000 + cash: 5,000)

ISIN           Label   Current   Target   Drift     Buy (PLN)
IE00BK5BQT80   VWCE    56.25%    60.00%   +3.75pp   3,000.00
IE00B4L5Y983   IWDA    37.50%    40.00%   +2.50pp   2,000.00
──────────────────────────────────────────────────────────────
Cash deployed: 5,000.00 PLN
Leftover cash: 0.00 PLN
```

## 7. Architecture

```
driftless/
├── pyproject.toml
├── README.md
├── examples/
│   └── portfolio.example.json
├── src/driftless/
│   ├── __init__.py
│   ├── __main__.py          # python -m driftless
│   ├── cli.py               # typer entry
│   ├── models.py            # dataclasses: Portfolio, Position, Target, Plan
│   ├── loader.py            # JSON load + validation
│   ├── engine.py            # buy-only algorithm
│   ├── validate.py          # business rule checks
│   └── formatters/
│       ├── table.py         # rich table
│       └── json_out.py
├── schemas/
│   └── portfolio.schema.json
└── tests/
    ├── test_loader.py
    ├── test_engine.py
    └── fixtures/
        └── sample_portfolio.json
```

### Module responsibilities

- **models.py** — immutable dataclasses; no I/O
- **loader.py** — parse JSON → `Portfolio`; JSON Schema structural validation
- **validate.py** — business rules (weights sum, duplicate ISIN, etc.)
- **engine.py** — pure function: `Portfolio → RebalancePlan`
- **formatters/** — presentation only
- **cli.py** — wires commands; exit codes (0 ok, 1 validation, 2 usage)

## 8. Tech Stack

| Choice | Rationale |
|---|---|
| Python ≥3.14 | User preference; dataclasses, modern typing |
| `pyproject.toml` + `uv` or `pip` | Standard packaging |
| `jsonschema` | Declarative input validation |
| `typer` | CLI UX |
| `rich` | Table formatting |
| `pytest` | Unit tests |

## 9. Testing Strategy

- **engine.py** — table-driven tests: balanced portfolio, scale-down, all overweight, new ISIN at 0
- **loader.py** — invalid JSON, bad ISIN, weight sum errors
- **fixtures** — anonymized example matching README
- No network calls in v1 tests

## 10. Future (v1.1+)

- `--deploy N` quick mode (cash override)
- NBP FX helper: `value_eur` → `value_pln`
- CSV broker export adapter
- `driftless init` scaffold template

## 11. Open Source Positioning

- MIT license
- README with disclaimer: not financial advice, no tax calculations
- `examples/portfolio.example.json` with fictional values
- Polish + English README sections (user's brand: finanse + dev)
