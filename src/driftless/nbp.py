import json
import urllib.request
from urllib.error import URLError


def fetch_nbp_rate(currency: str) -> float:
    """Fetch the latest mid exchange rate in PLN from NBP (Table A) for a given currency."""
    currency = currency.upper()
    if currency == "PLN":
        return 1.0

    url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency}/?format=json"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        # 5 second timeout to keep CLI highly responsive
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return float(data["rates"][0]["mid"])
    except URLError as exc:
        raise RuntimeError(
            f"Failed to fetch NBP exchange rate for {currency} (API offline or no network): {exc}"
        )
