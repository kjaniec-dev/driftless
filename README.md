# Driftless

**Buy-only UCITS portfolio rebalancer for Polish investors.**  
Snapshot in → concrete PLN buy orders out. No sells, no tax engine, no broker API integration.

Python **3.10+** (developed and tested on 3.14) · MIT · Open Source

---

## Why use Driftless?

If you hold a basket of UCITS ETFs, a target allocation, and have some cash on your account (or a fresh deposit), calculating exactly how much of each ETF to buy (e.g., VWCE vs. IWDA) can be tedious. Selling overweight assets is often not an option due to transaction costs, capital gains taxes, or a strict "buy-only" strategy.

**Driftless** reads your current portfolio snapshot from a single JSON file and outputs **precise buy orders in PLN** per ISIN to bring you as close as possible to your target allocation — solely through purchasing underweight assets, without triggering any sell orders.

---

## Typical Workflow

1. Open your broker app and copy the current value of your positions (already converted to or held in PLN).
2. Copy your free cash balance.
3. Fill out or update your `portfolio.json` (use `driftless init` to generate a starter template).
4. Run:
   ```bash
   driftless plan portfolio.json
   ```
5. Manually place the calculated buy orders at your broker.

---

## Quick Start

### Installation

```bash
git clone https://github.com/yourusername/driftless.git && cd driftless
python3 -m venv .venv
source .venv/bin/activate   # On Windows use: .venv\Scripts\activate
pip install -e .
```

To run with development and testing dependencies:
```bash
pip install -e ".[dev]"
pytest
```

### No Python Experience?

Driftless requires a one-time Python (3.10+) installation and typing a few commands in your terminal. The configuration itself is a clean, easy-to-edit JSON file.

If using a terminal is a barrier, consider these simpler deployment options:
* **pipx** — Install globally without managing a virtual environment manually:
  ```bash
  pipx install driftless
  driftless plan portfolio.json
  ```
* **Stand-alone Executable** *(Planned)* — A single binary executable (via PyInstaller) that runs without Python installed at all.

---

## Commands

| Command | Description |
|---|---|
| `driftless init [file]` | Creates a ready-to-edit `portfolio.json` (defaults to the current directory) |
| `driftless plan <file.json>` | Calculates the purchase plan and prints a formatted terminal table |
| `driftless plan <file.json> --json` | Outputs the plan as machine-readable JSON (useful for scripts/logging) |
| `driftless validate <file.json>` | Performs schema and business rule validation only |

### Exit Codes
* `0` — Success / OK
* `1` — File validation error (invalid JSON, schema violation, or target weights do not sum to 1.0)
* `2` — Usage error (missing file, unreadable file, or invalid CLI parameters)

Errors are printed as a single, clean line on `stderr` without exposing a Python traceback.

---

## Portfolio File Format

Your portfolio file is a **full snapshot** representing your positions and free cash at a given point in time (`as_of`).

```json
{
  "base_currency": "PLN",
  "as_of": "2026-06-03",
  "cash_pln": 5000,
  "positions": [
    { "isin": "IE00BK5BQT80", "value_pln": 45000, "label": "VWCE" },
    { "isin": "IE00B4L5Y983", "value_pln": 30000, "label": "IWDA" }
  ],
  "target": [
    { "isin": "IE00BK5BQT80", "weight": 0.60 },
    { "isin": "IE00B4L5Y983", "weight": 0.40 }
  ]
}
```

### Field Specification

| Field | Required | Description |
|---|---|---|
| `base_currency` | Yes | Must be `"PLN"` in v1. |
| `as_of` | No | ISO date string for audit purposes. |
| `cash_pln` | Yes | Your total free cash balance on the brokerage account (must be `≥ 0`). |
| `positions[].isin` | Yes | UCITS ISIN (12 uppercase alphanumeric characters). |
| `positions[].value_pln`| Yes | Current market value of the position in PLN. |
| `positions[].label` | No | Short ticker or custom label (e.g. `"VWCE"`) to display in tables. |
| `target[].isin` | Yes | Target asset ISIN. If missing from `positions`, it is treated as having `value_pln: 0`. |
| `target[].weight` | Yes | Target allocation weight decimal (between `0` and `1`). **All weights must sum to 1.0.** |

> **FX Note:** All position values must be supplied in PLN. The tool does not automatically fetch live exchange rates (keeping the codebase offline-first and simple); an NBP FX exchange rate helper is planned for future versions.

---

## How it Calculates the Plan (Buy-Only)

1. **Calculate Total Assets:**
   ```
   total = sum(position.value_pln) + cash_pln
   ```
2. **Calculate Target Value per ISIN:**
   ```
   target_value[isin] = total × weight
   ```
3. **Determine Allocation Gap:**
   ```
   gap[isin] = target_value[isin] - current_value[isin]
   buy_raw[isin] = max(0, gap[isin])
   ```
4. **Scale to Available Cash:**  
   If the sum of all raw buy orders exceeds `cash_pln`, Driftless **scales the orders down proportionally** to fully deploy the available cash. Any leftover fractional cash is reported as `leftover_cash`.

Since no selling occurs, **overweight assets cannot be adjusted**. Driftless accepts this reality, shows the drift, and directs 100% of available cash to the most underweight assets to reduce overall tracking error.

---

## Example Output

```
Driftless — plan as of 2026-06-03
Total portfolio: 80,000 PLN  (positions: 75,000 + cash: 5,000)

┏━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┓
┃ ISIN         ┃ Label ┃ Current ┃ Target ┃   Drift ┃ Buy (PLN) ┃
┡━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━┩
│ IE00BK5BQT80 │ VWCE  │  56.25% │ 60.00% │ +3.75pp │  3,000.00 │
│ IE00B4L5Y983 │ IWDA  │  37.50% │ 40.00% │ +2.50pp │  2,000.00 │
└──────────────┴───────┴─────────┴────────┴─────────┴───────────┘

Cash deployed: 5,000.00 PLN
Leftover cash: 0.00 PLN
```

---

## What Driftless does NOT do

* **Tax calculations** (no capital gains, PIT-38, FIFO, or tax-loss harvesting logic).
* **Automatic broker imports** or API execution (no read/write keys required).
* **Live market pricing** (you provide the snapshot, keeping your data private).
* **Investment advice**.

This is purely a mathematical utility tool to assist your regular portfolio management.

---

## Roadmap

- [ ] `--deploy N` — Override available cash for a specific transaction without altering the snapshot.
- [ ] NBP FX Helper — Add a subcommand to convert foreign-currency values (EUR, USD) to PLN using official NBP exchange rates.
- [ ] Broker CSV Adapters — Simple parsers to bootstrap or update portfolio values from popular Polish/EU broker CSV exports.
- [ ] Stand-alone Binaries — Release single-file executables via PyInstaller.

---

## Development

All tests run completely offline and require no network connectivity.

```bash
pip install -e ".[dev]"
pytest -v
python -m driftless plan examples/portfolio.example.json
```

### Directory Structure

```
src/driftless/          CLI implementation, loader, engine, and formatters
src/driftless/schemas/  JSON Schema (bundled with the package)
tests/                  pytest test suite
examples/               Sample portfolio JSON files
```

---

## Disclaimer

This software is provided for personal financial arithmetic only. It is not investment advice, legal advice, or tax advice. You are solely responsible for your investment decisions and compliance with local laws and tax regulations.

## License

MIT — See [LICENSE](LICENSE) for the full text.
