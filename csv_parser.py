import pandas as pd
from io import BytesIO


COLUMN_ALIASES = {
    "stock_name": [
        "stock_name",
        "stock",
        "name",
        "company",
        "company_name",
        "ticker",
        "symbol",
    ],
    "quantity": [
        "quantity",
        "qty",
        "shares",
        "share_count",
        "no_of_shares",
        "units",
    ],
    "avg_buy_price": [
        "avg_buy_price",
        "average_buy_price",
        "avg_cost",
        "avg_cost_price",
        "buy_price",
        "avg_price",
        "purchase_price",
        "avg_purchase_price",
        "cost_price",
        "avg_cost_per_share",
    ],
    "buy_value": [
        "buy_value",
        "investment_value",
        "invested_value",
        "invested_amount",
        "amount_invested",
        "total_buy_value",
        "total_invested",
        "cost_value",
        "investment_amount",
        "total_investment",
    ],
}


def _normalize_columns(columns):
    return [column.strip().lower().replace(" ", "_") for column in columns]


def _find_column(columns, aliases):
    for alias in aliases:
        if alias in columns:
            return alias
    return None


def _load_dataframe(file) -> pd.DataFrame:
    filename = getattr(file, "name", "") or ""
    filename = filename.lower()
    file.seek(0)

    if filename.endswith((".xls", ".xlsx")):
        return pd.read_excel(file, header=None, dtype=str)

    return pd.read_csv(file, header=None, dtype=str)


def _detect_header_row(raw: pd.DataFrame) -> tuple[int | None, list[str] | None]:
    for idx in range(min(50, len(raw))):
        row = raw.iloc[idx].fillna("").astype(str).tolist()
        normalized = _normalize_columns(row)
        if (
            _find_column(normalized, COLUMN_ALIASES["stock_name"]) is not None
            and _find_column(normalized, COLUMN_ALIASES["quantity"]) is not None
        ):
            return idx, normalized
    return None, None


def _load_parsable_dataframe(file) -> pd.DataFrame:
    file.seek(0)
    raw = _load_dataframe(file)
    header_idx, header = _detect_header_row(raw)
    if header_idx is not None and header is not None:
        df = raw.iloc[header_idx + 1 :].copy()
        df.columns = header
        df = df.reset_index(drop=True)
        df.columns = _normalize_columns(df.columns)
        return df

    file.seek(0)
    # Fallback to normal parsing for well-formed input
    filename = getattr(file, "name", "") or ""
    filename = filename.lower()
    if filename.endswith((".xls", ".xlsx")):
        return pd.read_excel(file)
    return pd.read_csv(file)


def parse_csv(file) -> pd.DataFrame:
    df = _load_parsable_dataframe(file)
    df.columns = _normalize_columns(df.columns)

    found_columns = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        found = _find_column(df.columns, aliases)
        if found:
            found_columns[canonical] = found

    if "stock_name" not in found_columns:
        raise ValueError(
            "Missing required stock_name column. Supported names: stock_name, stock, name, company, ticker, symbol."
        )
    if "quantity" not in found_columns:
        raise ValueError(
            "Missing required quantity column. Supported names: quantity, qty, shares, share_count, no_of_shares."
        )
    if "avg_buy_price" not in found_columns and "buy_value" not in found_columns:
        raise ValueError(
            "Missing required price data. Supply avg_buy_price or buy_value. Supported names: avg_buy_price, average_buy_price, buy_price, invested_value, amount_invested."
        )

    df = df.rename(
        columns={
            found_columns["stock_name"]: "stock_name",
            found_columns["quantity"]: "quantity",
            **(
                {found_columns["avg_buy_price"]: "avg_buy_price"}
                if "avg_buy_price" in found_columns
                else {}
            ),
            **(
                {found_columns["buy_value"]: "buy_value"}
                if "buy_value" in found_columns
                else {}
            ),
        }
    )

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    if "avg_buy_price" in df.columns:
        df["avg_buy_price"] = pd.to_numeric(df["avg_buy_price"], errors="coerce")
    if "buy_value" in df.columns:
        df["buy_value"] = pd.to_numeric(df["buy_value"], errors="coerce")

    if "avg_buy_price" not in df.columns:
        df["avg_buy_price"] = df["buy_value"] / df["quantity"]
    if "buy_value" not in df.columns:
        df["buy_value"] = df["quantity"] * df["avg_buy_price"]

    missing_values = df[["stock_name", "quantity", "avg_buy_price", "buy_value"]].isna().any(axis=1)
    if missing_values.any():
        invalid_rows = missing_values.sum()
        raise ValueError(
            f"Found {invalid_rows} invalid row(s) after normalization. Check stock_name, quantity and price values."
        )

    for col in ["closing_price", "closing_value", "unrealized_pnl"]:
        if col not in df.columns:
            df[col] = None

    return df[["stock_name", "quantity", "avg_buy_price", "buy_value", "closing_price", "closing_value", "unrealized_pnl"]]
