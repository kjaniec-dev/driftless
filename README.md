# Driftless

**Buy-only UCITS rebalancer for Polish investors.**  
Snapshot in → concrete PLN buy orders out. No sells, no tax engine, no broker API.

Python **3.14+** · MIT · open source

---

## Po polsku

### Po co to jest

Masz koszyk ETF-ów UCITS, docelową alokację i środki na koncie (albo świeżą wpłatę). Ręcznie liczenie „ile kupić VWCE, ile IWDA” przy każdym dokupieniu jest żmudne — a sprzedaż overweightu często nie wchodzi w grę (koszty, podatki, zwyczaj „tylko dokupuję”).

**Driftless** bierze aktualny stan portfela z jednego pliku JSON i zwraca **konkretne kwoty kupna w PLN** per ISIN, żeby zbliżyć się do targetu — wyłącznie przez kupno, bez zleceń sprzedaży.

### Typowy workflow

1. W aplikacji brokera skopiuj wartości pozycji (w PLN lub przelicz je sam).
2. Wpisz wolny cash na koncie.
3. Uzupełnij `portfolio.json` (szablon: `examples/portfolio.example.json`).
4. Uruchom:

   ```bash
   driftless plan portfolio.json
   ```

5. Złóż zlecenia kupna ręcznie u brokera.

### Instalacja

```bash
git clone <repo-url> driftless && cd driftless
python3.14 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

Opcjonalnie z testami:

```bash
pip install -e ".[dev]"
pytest
```

### Dla osoby, która nie zna Pythona

Wymagana jest jednorazowa instalacja Pythona 3.14 i wpisanie kilku komend w terminalu (sekcja „Instalacja” powyżej). Sam plik konfiguracyjny jest już maksymalnie prosty — to jeden czytelny JSON, a `driftless init` generuje gotowy szablon do edycji w zwykłym edytorze tekstu.

Jeśli komfortowe wpisywanie komend w terminalu jest barierą, najwygodniejsze opcje to:

- **pipx** — instalacja jedną komendą bez ręcznego venv: `pipx install driftless`, potem po prostu `driftless plan portfolio.json` z dowolnego katalogu.
- **gotowy plik wykonywalny** (planowane) — pojedynczy binarny plik (PyInstaller), bez instalowania Pythona; uruchamiany podwójnym kliknięciem / z terminala.

Czego raczej nie da się uprościć bez zmiany charakteru narzędzia: to jest CLI, więc minimum to otwarcie terminala i podanie ścieżki do pliku. GUI/web to osobny, większy projekt.

### Komendy

| Komenda | Opis |
|---|---|
| `driftless init [plik]` | Tworzy gotowy do edycji `portfolio.json` (domyślnie w bieżącym katalogu) |
| `driftless plan <plik.json>` | Liczy plan kupna i drukuje tabelę |
| `driftless plan <plik> --json` | Ten sam wynik w JSON (skrypty, notatki) |
| `driftless validate <plik>` | Tylko walidacja schematu i reguł biznesowych |

Kody wyjścia: `0` = OK, `1` = błąd zawartości pliku (zły JSON / schemat / wagi), `2` = problem z plikiem (brak/nieczytelny) lub złe użycie. Błędy są drukowane jako jedna czytelna linia na `stderr` — bez pythonowego tracebacku.

### Najszybszy start

```bash
driftless init            # tworzy portfolio.json z przykładem
# edytuj portfolio.json w dowolnym edytorze
driftless plan portfolio.json
```

### Format pliku portfela

Jeden plik JSON — **pełny snapshot**: pozycje + wolny cash = cały portfel w momencie `as_of`.

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

| Pole | Wymagane | Znaczenie |
|---|---|---|
| `base_currency` | tak | W v1 tylko `"PLN"` |
| `as_of` | nie | Data snapshotu (audyt: „te liczby z tego dnia”) |
| `cash_pln` | tak | Cały wolny gotówkowy saldo na koncie (≥ 0) |
| `positions[].isin` | tak | ISIN UCITS (12 znaków, wielkie litery) |
| `positions[].value_pln` | tak | Aktualna wartość pozycji w PLN |
| `positions[].label` | nie | Ticker / nazwa do tabeli (np. `VWCE`) |
| `target[].isin` | tak | ISIN z targetu; brak w `positions` = 0 PLN |
| `target[].weight` | tak | Udział docelowy; **suma wag = 1.0** |

**FX:** W v1 wszystkie kwoty podajesz już w PLN (np. po kursie brokera). Narzędzie nie pobiera kursów NBP — to świadoma prostota; helper FX planowany na później.

### Jak liczy plan (buy-only)

```
total     = suma(value_pln pozycji) + cash_pln
target[i] = total × waga[i]
gap[i]    = target[i] − current[i]
buy[i]    = max(0, gap[i])                    # tylko niedoważenie
```

Jeśli suma `buy` > `cash_pln`, zlecenia są **proporcjonalnie skalowane** w dół. Nadwyżka cash zostaje jako `leftover_cash` w outputcie.

Bez sprzedaży **nie da się idealnie trafić w target**, gdy coś jest overweight — narzędzie tego nie ukrywa, tylko pokazuje drift i kupuje to, co da się naprawić gotówką.

### Przykładowy wynik

```
Driftless — plan as of 2026-06-03
Total portfolio: 80,000 PLN  (positions: 75,000 + cash: 5,000)

ISIN           Label   Current   Target   Drift     Buy (PLN)
IE00BK5BQT80   VWCE    56.25%    60.00%   +3.75pp   3,000.00
IE00B4L5Y983   IWDA    37.50%    40.00%   +2.50pp   2,000.00

Cash deployed: 5,000.00 PLN
Leftover cash: 0.00 PLN
```

### Czego Driftless nie robi

- Podatku (PIT, FIFO, koszt nabycia)
- Zleceń sprzedaży ani tax-loss harvesting
- Importu z brokera / API
- Pobierania cen z rynku
- Rekomendacji inwestycyjnych

To narzędzie do **arytmetyki portfela**, nie doradztwa.

### Roadmap

- [ ] `--deploy` — nadpisanie kwoty cash do rozłożenia
- [ ] Helper NBP: `value_eur` → `value_pln`
- [ ] Import CSV z brokera
- [ ] `driftless init` — szablon pliku

---

## English

### What it does

You hold a UCITS ETF basket, a target allocation, and cash on account (or a fresh deposit). Manually splitting “how much VWCE vs IWDA” each time is tedious; selling overweight legs is often off the table.

**Driftless** reads one JSON snapshot and returns **specific PLN buy amounts per ISIN** to reduce allocation drift — buy-only, no sell orders.

### Install & run

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -e .
driftless plan examples/portfolio.example.json
driftless validate examples/portfolio.example.json
driftless plan portfolio.json --json
```

See the Polish section above for the full JSON schema, algorithm, and example table output.

### Design choices

| Choice | Why |
|---|---|
| ISIN as key | Unambiguous for UCITS across exchanges |
| PLN base in v1 | Matches typical PL broker workflow; you supply converted values |
| Full snapshot | Positions + all free cash = correct `total` for drift math |
| Buy-only | Matches recurring contribution / DCA without triggering sells |

---

## Development

```bash
pip install -e ".[dev]"
pytest -v
python -m driftless plan examples/portfolio.example.json
```

Layout:

```
src/driftless/     CLI, loader, engine, formatters
schemas/           JSON Schema for portfolio files
tests/             pytest (no network)
examples/          Sample portfolio JSON
```

---

## Disclaimer

This software is provided for **personal portfolio arithmetic** only. It is not financial, legal, or tax advice. You are responsible for your own investment decisions and compliance with local regulations.

## License

MIT — see [LICENSE](LICENSE) if present, otherwise MIT as stated in `pyproject.toml`.
