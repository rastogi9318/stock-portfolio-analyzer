import pandas as pd


REQUIRED_COLUMNS = ["stock_name", "quantity", "avg_buy_price"]


def parse_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    df.columns = [column.strip().lower().replace(" ", "_") for column in df.columns]

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # normalize types
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["avg_buy_price"] = pd.to_numeric(df["avg_buy_price"], errors="coerce")

    # compute buy value and ensure expected columns exist for downstream code
    df["buy_value"] = df["quantity"] * df["avg_buy_price"]

    for col in ["closing_price", "closing_value", "unrealized_pnl"]:
        if col not in df.columns:
            df[col] = None

    return df[["stock_name", "quantity", "avg_buy_price", "buy_value", "closing_price", "closing_value", "unrealized_pnl"]]
