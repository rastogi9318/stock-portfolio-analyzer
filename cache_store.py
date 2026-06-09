import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


CACHE_DB = Path("stock_analyzer_cache.sqlite3")
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


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(CACHE_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("pragma journal_mode = wal")
    conn.execute("pragma busy_timeout = 30000")
    conn.execute(
        """
        create table if not exists symbol_cache (
            stock_name text primary key,
            symbol text,
            status text not null,
            error_message text,
            fetched_at text not null
        )
        """
    )
    conn.execute(
        """
        create table if not exists metrics_cache (
            symbol text primary key,
            qoq_profit_change_pct real,
            fii_change_pct real,
            dii_change_pct real,
            roce_change real,
            roe_change real,
            debt_to_equity real,
            promoter_holding_pct real,
            pledged_shares_pct real,
            sales_growth_pct real,
            pe_ratio real,
            industry_pe real,
            status text not null,
            error_message text,
            fetched_at text not null
        )
        """
    )
    _ensure_metric_columns(conn)
    conn.commit()


def _ensure_metric_columns(conn: sqlite3.Connection) -> None:
    existing = {
        row["name"]
        for row in conn.execute("pragma table_info(metrics_cache)").fetchall()
    }
    added_column = False
    for column in METRIC_COLUMNS:
        if column not in existing:
            conn.execute(f"alter table metrics_cache add column {column} real")
            added_column = True
    if added_column:
        conn.execute("update metrics_cache set fetched_at = '1970-01-01T00:00:00'")


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
    with _connect() as conn:
        row = conn.execute(
            "select * from symbol_cache where stock_name = ?", (key,)
        ).fetchone()

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
    with _connect() as conn:
        conn.execute(
            """
            insert into symbol_cache
                (stock_name, symbol, status, error_message, fetched_at)
            values (?, ?, ?, ?, ?)
            on conflict(stock_name) do update set
                symbol = excluded.symbol,
                status = excluded.status,
                error_message = excluded.error_message,
                fetched_at = excluded.fetched_at
            """,
            (key, symbol, status, error_message, _now_iso()),
        )
        conn.commit()


def get_cached_metrics(symbol: str) -> dict | None:
    key = symbol.strip().upper()
    with _connect() as conn:
        row = conn.execute(
            "select * from metrics_cache where symbol = ?", (key,)
        ).fetchone()

    if row is None or not _is_fresh(row["fetched_at"]):
        return None
    return {
        "metrics": {column: row[column] for column in METRIC_COLUMNS},
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
    columns = ["symbol", *METRIC_COLUMNS, "status", "error_message", "fetched_at"]
    placeholders = ", ".join("?" for _ in columns)
    updates = ", ".join(
        f"{column} = excluded.{column}" for column in columns if column != "symbol"
    )
    values = [
        key,
        *[metrics.get(column) for column in METRIC_COLUMNS],
        status,
        error_message,
        _now_iso(),
    ]
    with _connect() as conn:
        conn.execute(
            f"""
            insert into metrics_cache ({", ".join(columns)})
            values ({placeholders})
            on conflict(symbol) do update set {updates}
            """,
            values,
        )
        conn.commit()
