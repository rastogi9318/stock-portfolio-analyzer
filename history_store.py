import sqlite3
from datetime import datetime
from pathlib import Path


HISTORY_DB = Path("stock_analyzer_history.sqlite3")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(HISTORY_DB, timeout=30)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("pragma journal_mode = wal")
    conn.execute("pragma busy_timeout = 30000")
    conn.execute(
        """
        create table if not exists analysis_runs (
            run_id integer primary key autoincrement,
            run_at text not null,
            stock_count integer not null,
            buy_count integer not null,
            hold_count integer not null,
            sell_count integer not null,
            na_count integer not null,
            total_buy_value real,
            total_closing_value real,
            total_unrealized_pnl real,
            avg_score real
        )
        """
    )
    conn.execute(
        """
        create table if not exists analysis_items (
            item_id integer primary key autoincrement,
            run_id integer not null,
            stock_name text not null,
            nse_symbol text,
            score real,
            recommendation text,
            closing_value real,
            unrealized_pnl real,
            explanation text,
            foreign key (run_id) references analysis_runs(run_id)
        )
        """
    )
    conn.commit()


def latest_items_by_symbol() -> dict:
    with _connect() as conn:
        latest_run = conn.execute(
            "select run_id from analysis_runs order by run_id desc limit 1"
        ).fetchone()
        if latest_run is None:
            return {}

        rows = conn.execute(
            """
            select stock_name, nse_symbol, score, recommendation
            from analysis_items
            where run_id = ?
            """,
            (latest_run["run_id"],),
        ).fetchall()

    return {
        (row["nse_symbol"] or row["stock_name"]).upper(): {
            "previous_score": row["score"],
            "previous_recommendation": row["recommendation"],
        }
        for row in rows
    }


def save_analysis_run(results) -> int:
    rec_counts = results["recommendation"].value_counts()
    numeric_score = results["score"].dropna()
    run_at = datetime.now().isoformat(timespec="seconds")

    with _connect() as conn:
        cursor = conn.execute(
            """
            insert into analysis_runs (
                run_at,
                stock_count,
                buy_count,
                hold_count,
                sell_count,
                na_count,
                total_buy_value,
                total_closing_value,
                total_unrealized_pnl,
                avg_score
            )
            values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_at,
                len(results),
                int(rec_counts.get("BUY", 0)),
                int(rec_counts.get("HOLD", 0)),
                int(rec_counts.get("SELL", 0)),
                int(rec_counts.get("N/A", 0)),
                _sum_column(results, "buy_value"),
                _sum_column(results, "closing_value"),
                _sum_column(results, "unrealized_pnl"),
                float(numeric_score.mean()) if not numeric_score.empty else None,
            ),
        )
        run_id = cursor.lastrowid

        for _, row in results.iterrows():
            conn.execute(
                """
                insert into analysis_items (
                    run_id,
                    stock_name,
                    nse_symbol,
                    score,
                    recommendation,
                    closing_value,
                    unrealized_pnl,
                    explanation
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    row.get("stock_name"),
                    row.get("nse_symbol"),
                    row.get("score"),
                    row.get("recommendation"),
                    row.get("closing_value"),
                    row.get("unrealized_pnl"),
                    row.get("explanation"),
                ),
            )
        conn.commit()
    return run_id


def load_recent_runs(limit: int = 10):
    with _connect() as conn:
        rows = conn.execute(
            """
            select *
            from analysis_runs
            order by run_id desc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def _sum_column(frame, column: str) -> float | None:
    if column not in frame:
        return None
    return float(frame[column].sum())
