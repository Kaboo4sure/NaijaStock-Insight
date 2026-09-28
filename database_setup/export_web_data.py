import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BASE_DIR.parent

DB_PATH = BASE_DIR / "naijastock.db"
HISTORICAL_DB_PATH = BASE_DIR / "historical_stock.db"
OUTPUT_DIR = REPOSITORY_ROOT / "site" / "data"
MAX_CHART_ROWS_PER_TICKER = 260


def table_exists(connection, table_name):
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
    """
    return connection.execute(query, (table_name,)).fetchone() is not None


def load_stock_data():
    frames = []

    if HISTORICAL_DB_PATH.exists():
        with sqlite3.connect(HISTORICAL_DB_PATH) as connection:
            if table_exists(connection, "historical_stock_data"):
                historical = pd.read_sql_query(
                    """
                    SELECT date, ticker, company_name, open, high, low,
                           close, volume
                    FROM historical_stock_data
                    """,
                    connection,
                )
                historical["source_priority"] = 0
                frames.append(historical)

    with sqlite3.connect(DB_PATH) as connection:
        current = pd.read_sql_query("SELECT * FROM stock_data", connection)
        current["source_priority"] = 1
        frames.append(current)

    stock_data = pd.concat(frames, ignore_index=True)
    stock_data["date"] = pd.to_datetime(stock_data["date"], errors="coerce")
    stock_data = (
        stock_data.dropna(subset=["date", "ticker", "close"])
        .sort_values(["ticker", "date", "source_priority"])
        .drop_duplicates(["ticker", "date"], keep="last")
        .groupby("ticker", group_keys=False)
        .tail(MAX_CHART_ROWS_PER_TICKER)
        .drop(columns="source_priority")
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )
    return stock_data


def export_data():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stock_data = load_stock_data()

    with sqlite3.connect(DB_PATH) as connection:
        if table_exists(connection, "weekly_signals"):
            signal_data = pd.read_sql_query(
                "SELECT * FROM weekly_signals ORDER BY date, ticker",
                connection,
            )
        else:
            signal_data = pd.DataFrame()

    stock_data.to_json(
        OUTPUT_DIR / "stocks.json",
        orient="records",
        date_format="iso",
    )

    signal_data.to_json(
        OUTPUT_DIR / "signals.json",
        orient="records",
        date_format="iso",
    )

    latest_stock_date = (
        str(stock_data["date"].max())
        if not stock_data.empty and "date" in stock_data.columns
        else None
    )

    latest_signal_date = (
        str(signal_data["date"].max())
        if not signal_data.empty and "date" in signal_data.columns
        else None
    )

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_stock_date": latest_stock_date,
        "latest_signal_date": latest_signal_date,
        "stock_records": len(stock_data),
        "signal_records": len(signal_data),
        "historical_source": (
            "Favourboi/nigerian-inflation-stock-analysis"
            if HISTORICAL_DB_PATH.exists()
            else None
        ),
        "chart_rows_per_ticker": MAX_CHART_ROWS_PER_TICKER,
    }

    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Exported {len(stock_data)} stock records.")
    print(f"Exported {len(signal_data)} signal records.")
    print(f"Website data saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    export_data()
