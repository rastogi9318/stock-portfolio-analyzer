import pandas as pd
import streamlit as st

from cache_store import METRIC_COLUMNS
from csv_parser import parse_csv
from exporter import to_csv_bytes
from history_store import latest_items_by_symbol, load_recent_runs, save_analysis_run
from scorer import score_stock_explained
from scraper import scrape_metrics_details
from symbol_resolver import resolve_symbol_details


RESULT_COLUMNS = [
    "nse_symbol",
    *METRIC_COLUMNS,
    "score",
    "recommendation",
    "explanation",
    "previous_score",
    "previous_recommendation",
    "score_change",
    "recommendation_change",
    "fetch_status",
    "data_source",
    "error_message",
]


def build_symbol_mapping(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        stock_name = row["stock_name"]
        resolved = resolve_symbol_details(stock_name)
        rows.append(
            {
                "stock_name": stock_name,
                "nse_symbol": resolved["symbol"] or "",
                "resolver_status": resolved["status"],
                "data_source": "cache" if resolved["from_cache"] else "screener",
                "error_message": resolved["error_message"] or "",
            }
        )
    return pd.DataFrame(rows)


def empty_result(symbol: str | None, status: str, error_message: str | None) -> dict:
    return {
        "nse_symbol": symbol,
        **{column: None for column in METRIC_COLUMNS},
        "score": 0,
        "recommendation": "N/A",
        "explanation": error_message or "No analysis was run for this stock.",
        "previous_score": None,
        "previous_recommendation": None,
        "score_change": None,
        "recommendation_change": "",
        "fetch_status": status,
        "data_source": "",
        "error_message": error_message or "",
    }


def color_rec(val):
    colors = {
        "BUY": "background-color: #c6efce",
        "SELL": "background-color: #ffc7ce",
        "HOLD": "background-color: #ffeb9c",
        "N/A": "background-color: #e5e7eb",
    }
    return colors.get(val, "")


def add_history_comparison(row: dict, previous_items: dict) -> dict:
    key = (row.get("nse_symbol") or "").upper()
    previous = previous_items.get(key)
    if previous is None:
        row["previous_score"] = None
        row["previous_recommendation"] = None
        row["score_change"] = None
        row["recommendation_change"] = "New"
        return row

    previous_score = previous["previous_score"]
    previous_rec = previous["previous_recommendation"]
    row["previous_score"] = previous_score
    row["previous_recommendation"] = previous_rec
    row["score_change"] = (
        row["score"] - previous_score
        if row.get("score") is not None and previous_score is not None
        else None
    )
    row["recommendation_change"] = (
        "Changed" if row.get("recommendation") != previous_rec else "Same"
    )
    return row


def show_portfolio_dashboard(results: pd.DataFrame) -> None:
    total_buy = results["buy_value"].sum()
    total_current = results["closing_value"].sum()
    total_pnl = results["unrealized_pnl"].sum()
    avg_score = results["score"].dropna().mean()

    cols = st.columns(4)
    cols[0].metric("Invested Value", f"{total_buy:,.0f}")
    cols[1].metric("Current Value", f"{total_current:,.0f}")
    cols[2].metric("Unrealized P&L", f"{total_pnl:,.0f}")
    cols[3].metric("Average Score", f"{avg_score:.2f}" if pd.notna(avg_score) else "N/A")

    rec_counts = results["recommendation"].value_counts().rename_axis("recommendation")
    st.bar_chart(rec_counts)

    review_count = results["fetch_status"].isin(["error", "parse_failed"]).sum()
    cache_count = (results["data_source"] == "cache").sum()
    st.caption(f"{cache_count} stock(s) served from cache. {review_count} need review.")


def show_history() -> None:
    recent_runs = load_recent_runs()
    if not recent_runs:
        return

    st.subheader("Historical Runs")
    history = pd.DataFrame(recent_runs)
    st.dataframe(history, use_container_width=True, hide_index=True)


st.set_page_config(page_title="Portfolio Analyzer", layout="wide")
st.title("Indian Stock Portfolio Analyzer")
show_history()

uploaded = st.file_uploader("Upload your portfolio CSV", type=["csv"])

if uploaded:
    try:
        df = parse_csv(uploaded)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.subheader("Portfolio Preview")
    st.dataframe(df, use_container_width=True)

    st.subheader("Symbol Mapping")
    st.caption("Edit nse_symbol if Screener resolves the wrong company.")
    symbol_mapping = build_symbol_mapping(df)
    edited_mapping = st.data_editor(
        symbol_mapping,
        use_container_width=True,
        hide_index=True,
        disabled=["stock_name", "resolver_status", "data_source", "error_message"],
        column_config={
            "nse_symbol": st.column_config.TextColumn(
                "nse_symbol", help="Manual override is allowed before analysis."
            )
        },
        key="symbol_mapping_editor",
    )

    if st.button("Run Analysis"):
        failed = []
        previous_items = latest_items_by_symbol()
        progress = st.progress(0)
        status = st.empty()
        n = len(df)
        extra_rows = []

        for position, (_, row) in enumerate(df.iterrows(), start=1):
            name = row["stock_name"]
            symbol = str(edited_mapping.loc[position - 1, "nse_symbol"]).strip().upper()
            status.text(f"Processing {name}...")

            if not symbol:
                failed.append(name)
                extra_rows.append(
                    add_history_comparison(
                        empty_result(symbol, "symbol_missing", "No symbol selected"),
                        previous_items,
                    )
                )
            else:
                details = scrape_metrics_details(symbol)
                metrics = details["metrics"]
                score, rec, explanation = score_stock_explained(metrics)
                result_row = {
                        "nse_symbol": symbol,
                        **metrics,
                        "score": score,
                        "recommendation": rec,
                        "explanation": explanation,
                        "fetch_status": details["status"],
                        "data_source": "cache" if details["from_cache"] else "screener",
                        "error_message": details["error_message"] or "",
                }
                extra_rows.append(add_history_comparison(result_row, previous_items))

                if details["status"] in {"error", "parse_failed"}:
                    failed.append(f"{name} ({symbol})")

            progress.progress(position / n)

        status.empty()
        extra_df = pd.DataFrame(extra_rows, columns=RESULT_COLUMNS)
        results = pd.concat(
            [df.reset_index(drop=True), extra_df.reset_index(drop=True)], axis=1
        )

        if failed:
            st.warning("Needs review: " + ", ".join(failed))

        run_id = save_analysis_run(results)
        st.success(f"Saved analysis run #{run_id}.")

        st.subheader("Portfolio Dashboard")
        show_portfolio_dashboard(results)

        styled = results.style.map(color_rec, subset=["recommendation"])
        st.subheader("Analysis Results")
        st.dataframe(styled, use_container_width=True)
        st.download_button(
            "Download Enriched CSV",
            to_csv_bytes(results),
            "portfolio_analysis.csv",
            "text/csv",
        )
