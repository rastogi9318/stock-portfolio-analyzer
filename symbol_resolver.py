import requests
from urllib.parse import urlparse

from cache_store import get_cached_symbol, save_symbol


_cache = {}


def _extract_symbol(company_url: str) -> str | None:
    parts = [part for part in urlparse(company_url).path.split("/") if part]
    try:
        company_index = parts.index("company")
    except ValueError:
        return None

    if company_index + 1 >= len(parts):
        return None
    return parts[company_index + 1]


def resolve_symbol(stock_name: str) -> str | None:
    return resolve_symbol_details(stock_name)["symbol"]


def resolve_symbol_details(stock_name: str, use_cache: bool = True) -> dict:
    if stock_name in _cache:
        return {
            "symbol": _cache[stock_name],
            "status": "ok",
            "error_message": None,
            "from_cache": True,
        }

    if use_cache:
        cached = get_cached_symbol(stock_name)
        if cached is not None:
            if cached["symbol"]:
                _cache[stock_name] = cached["symbol"]
            return cached

    try:
        resp = requests.get(
            "https://www.screener.in/api/company/search/",
            params={"q": stock_name},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data:
            symbol = _extract_symbol(data[0]["url"])
            if symbol:
                _cache[stock_name] = symbol
                save_symbol(stock_name, symbol, "ok")
                return {
                    "symbol": symbol,
                    "status": "ok",
                    "error_message": None,
                    "from_cache": False,
                }

        save_symbol(stock_name, None, "not_found", "No Screener search result")
        return {
            "symbol": None,
            "status": "not_found",
            "error_message": "No Screener search result",
            "from_cache": False,
        }
    except Exception as exc:
        error_message = str(exc)
        save_symbol(stock_name, None, "error", error_message)
        return {
            "symbol": None,
            "status": "error",
            "error_message": error_message,
            "from_cache": False,
        }
