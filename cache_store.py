from datetime import datetime, timedelta


CACHE_TTL_HOURS = 24

METRIC_COLUMNS = [
    "qoq_profit_change_pct",
    "fii_change_pct",
    "dii_change_pct",
    "roce_change",
    "roe_change",
    "debt_to_equity",
    "promoter_holding_pct",
    "pledged_shares_pct",
    "sales_growth_pct",
    "pe_ratio",
    "industry_pe",
]

_FALLBACK_STATE = {
    "symbol_cache": {},
    "metrics_cache": {},
}


def _state_bucket(name: str) -> dict:
    try:
        import streamlit as st

        if name not in st.session_state:
            st.session_state[name] = {}
        return st.session_state[name]
    except Exception:
        return _FALLBACK_STATE[name]


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _is_fresh(fetched_at: str) -> bool:
    try:
        fetched_time = datetime.fromisoformat(fetched_at)
    except ValueError:
        return False
    return datetime.utcnow() - fetched_time <= timedelta(hours=CACHE_TTL_HOURS)


def get_cached_symbol(stock_name: str) -> dict | None:
    key = stock_name.strip().lower()
    row = _state_bucket("symbol_cache").get(key)
    if row is None or not _is_fresh(row["fetched_at"]):
        return None

    return {
        "symbol": row["symbol"],
        "status": row["status"],
        "error_message": row["error_message"],
        "from_cache": True,
    }


def save_symbol(
    stock_name: str, symbol: str | None, status: str, error_message: str | None = None
) -> None:
    key = stock_name.strip().lower()
    _state_bucket("symbol_cache")[key] = {
        "symbol": symbol,
        "status": status,
        "error_message": error_message,
        "fetched_at": _now_iso(),
    }


def get_cached_metrics(symbol: str) -> dict | None:
    key = symbol.strip().upper()
    row = _state_bucket("metrics_cache").get(key)
    if row is None or not _is_fresh(row["fetched_at"]):
        return None

    return {
        "metrics": {column: row["metrics"].get(column) for column in METRIC_COLUMNS},
        "status": row["status"],
        "error_message": row["error_message"],
        "from_cache": True,
    }


def save_metrics(
    symbol: str,
    metrics: dict,
    status: str,
    error_message: str | None = None,
) -> None:
    key = symbol.strip().upper()
    _state_bucket("metrics_cache")[key] = {
        "metrics": {column: metrics.get(column) for column in METRIC_COLUMNS},
        "status": status,
        "error_message": error_message,
        "fetched_at": _now_iso(),
    }
