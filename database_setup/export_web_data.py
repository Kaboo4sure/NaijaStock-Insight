import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = BASE_DIR.parent

DB_PATH = BASE_DIR / "naijastock.db"
OUTPUT_DIR = REPOSITORY_ROOT / "site" / "data"


def table_exists(connection, table_name):
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
    """
    return connection.execute(query, (table_name,)).fetchone() is not None


def export_data():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        stock_data = pd.read_sql_query(
            "SELECT * FROM stock_data ORDER BY date, ticker",
            connection,
        )

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
        indent=2,
    )

    signal_data.to_json(
        OUTPUT_DIR / "signals.json",
        orient="records",
        date_format="iso",
        indent=2,
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
    }

    with open(OUTPUT_DIR / "metadata.json", "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)

    print(f"Exported {len(stock_data)} stock records.")
    print(f"Exported {len(signal_data)} signal records.")
    print(f"Website data saved in: {OUTPUT_DIR}")


if __name__ == "__main__":
    export_data()