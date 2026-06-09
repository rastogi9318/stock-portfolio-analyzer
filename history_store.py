from datetime import datetime


_FALLBACK_STATE = {
    "analysis_runs": [],
    "analysis_items": {},
    "next_run_id": 1,
}


def _state_value(name: str, default):
    try:
        import streamlit as st

        if name not in st.session_state:
            st.session_state[name] = default() if callable(default) else default
        return st.session_state[name]
    except Exception:
        if name not in _FALLBACK_STATE:
            _FALLBACK_STATE[name] = default() if callable(default) else default
        return _FALLBACK_STATE[name]


def latest_items_by_symbol() -> dict:
    runs = _state_value("analysis_runs", list)
    if not runs:
        return {}

    latest_run_id = runs[-1]["run_id"]
    items_by_run = _state_value("analysis_items", dict)
    rows = items_by_run.get(latest_run_id, [])
    return {
        (row["nse_symbol"] or row["stock_name"]).upper(): {
            "previous_score": row["score"],
            "previous_recommendation": row["recommendation"],
        }
        for row in rows
    }


def save_analysis_run(results) -> int:
    runs = _state_value("analysis_runs", list)
    items_by_run = _state_value("analysis_items", dict)
    run_id = _next_run_id()
    rec_counts = results["recommendation"].value_counts()
    numeric_score = results["score"].dropna()

    runs.append(
        {
            "run_id": run_id,
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "stock_count": len(results),
            "buy_count": int(rec_counts.get("BUY", 0)),
            "hold_count": int(rec_counts.get("HOLD", 0)),
            "sell_count": int(rec_counts.get("SELL", 0)),
            "na_count": int(rec_counts.get("N/A", 0)),
            "total_buy_value": _sum_column(results, "buy_value"),
            "total_closing_value": _sum_column(results, "closing_value"),
            "total_unrealized_pnl": _sum_column(results, "unrealized_pnl"),
            "avg_score": float(numeric_score.mean()) if not numeric_score.empty else None,
        }
    )

    items_by_run[run_id] = [
        {
            "stock_name": row.get("stock_name"),
            "nse_symbol": row.get("nse_symbol"),
            "score": row.get("score"),
            "recommendation": row.get("recommendation"),
            "closing_value": row.get("closing_value"),
            "unrealized_pnl": row.get("unrealized_pnl"),
            "explanation": row.get("explanation"),
        }
        for _, row in results.iterrows()
    ]
    return run_id


def load_recent_runs(limit: int = 10):
    runs = _state_value("analysis_runs", list)
    return list(reversed(runs[-limit:]))


def _next_run_id() -> int:
    try:
        import streamlit as st

        if "next_run_id" not in st.session_state:
            st.session_state["next_run_id"] = 1
        run_id = st.session_state["next_run_id"]
        st.session_state["next_run_id"] += 1
        return run_id
    except Exception:
        run_id = _FALLBACK_STATE["next_run_id"]
        _FALLBACK_STATE["next_run_id"] += 1
        return run_id


def _sum_column(frame, column: str) -> float | None:
    if column not in frame:
        return None
    return float(frame[column].sum())
