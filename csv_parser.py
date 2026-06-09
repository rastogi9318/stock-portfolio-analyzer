import pandas as pd


REQUIRED_COLUMNS = [
    "stock_name",
    "quantity",
    "avg_buy_price",
    "buy_value",
    "closing_price",
    "closing_value",
    "unrealized_pnl",
]


def parse_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    df.columns = [column.strip().lower().replace(" ", "_") for column in df.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df[REQUIRED_COLUMNS]
