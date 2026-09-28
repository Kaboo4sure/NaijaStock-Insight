"""Download and validate the prototype NGX historical dataset.

The source repository does not currently include an explicit licence.  This
script therefore keeps the downloaded rows in an ignored, temporary SQLite
database.  Only the compact dashboard output generated from those rows is
committed to this repository.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE = BASE_DIR / "historical_stock.db"
SOURCE_COMMIT = "ea67d0f82a70dfaf682a35dc47a3b95f0b75db3c"
DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/Favourboi/"
    "nigerian-inflation-stock-analysis/"
    f"{SOURCE_COMMIT}/NGX%20Stocks%202000%20-%202025.csv"
)

REQUIRED_COLUMNS = {
    "Symbol",
    "Date",
    "Price",
    "Open",
    "High",
    "Low",
    "Volume",
    "Company Name",
    "Sector",
    "Market Cap",
}


def normalize_chunk(raw_data: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    missing_columns = sorted(REQUIRED_COLUMNS.difference(raw_data.columns))
    if missing_columns:
        raise ValueError(f"Source is missing columns: {missing_columns}")

    data = pd.DataFrame(
        {
            "date": pd.to_datetime(raw_data["Date"], errors="coerce"),
            "ticker": raw_data["Symbol"].astype("string").str.strip().str.upper(),
            "company_name": raw_data["Company Name"].astype("string").str.strip(),
            "sector": raw_data["Sector"].astype("string").str.strip(),
            "open": pd.to_numeric(raw_data["Open"], errors="coerce"),
            "high": pd.to_numeric(raw_data["High"], errors="coerce"),
            "low": pd.to_numeric(raw_data["Low"], errors="coerce"),
            "close": pd.to_numeric(raw_data["Price"], errors="coerce"),
            "volume": pd.to_numeric(raw_data["Volume"], errors="coerce"),
            "market_cap": pd.to_numeric(raw_data["Market Cap"], errors="coerce"),
        }
    )

    valid_rows = (
        data["date"].notna()
        & data["ticker"].notna()
        & data["ticker"].ne("")
        & data["company_name"].notna()
        & data["close"].gt(0)
    )
    rejected_count = int((~valid_rows).sum())
    data = data.loc[valid_rows].copy()

    # Zero OHLC values occur in the source and are treated as unavailable.
    for column in ("open", "high", "low"):
        data.loc[data[column] <= 0, column] = pd.NA

    data.loc[data["volume"] < 0, "volume"] = pd.NA
    data["date"] = data["date"].dt.strftime("%Y-%m-%d")
    data = data.drop_duplicates(["date", "ticker"], keep="last")
    return data, rejected_count


def create_staging_table(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS historical_stock_data_staging")
    connection.execute(
        """
        CREATE TABLE historical_stock_data_staging (
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            company_name TEXT NOT NULL,
            sector TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL NOT NULL,
            volume INTEGER,
            market_cap REAL,
            PRIMARY KEY (date, ticker)
        )
        """
    )


def insert_chunk(connection: sqlite3.Connection, data: pd.DataFrame) -> None:
    rows = data.astype(object).where(pd.notna(data), None).itertuples(
        index=False,
        name=None,
    )
    connection.executemany(
        """
        INSERT OR REPLACE INTO historical_stock_data_staging (
            date, ticker, company_name, sector, open, high, low, close,
            volume, market_cap
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def import_historical_data(source: str, database: Path) -> dict[str, object]:
    database.parent.mkdir(parents=True, exist_ok=True)
    total_source_rows = 0
    total_rejected_rows = 0

    with sqlite3.connect(database) as connection:
        create_staging_table(connection)

        for raw_chunk in pd.read_csv(source, chunksize=50_000):
            total_source_rows += len(raw_chunk)
            normalized, rejected = normalize_chunk(raw_chunk)
            total_rejected_rows += rejected
            insert_chunk(connection, normalized)

        summary = connection.execute(
            """
            SELECT COUNT(*), COUNT(DISTINCT ticker), MIN(date), MAX(date)
            FROM historical_stock_data_staging
            """
        ).fetchone()

        row_count, ticker_count, minimum_date, maximum_date = summary
        if row_count < 100_000 or ticker_count < 100:
            raise ValueError(
                "Historical-data validation failed: "
                f"only {row_count} rows and {ticker_count} tickers were accepted."
            )

        connection.execute("DROP TABLE IF EXISTS historical_stock_data")
        connection.execute(
            "ALTER TABLE historical_stock_data_staging "
            "RENAME TO historical_stock_data"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_historical_ticker_date "
            "ON historical_stock_data (ticker, date)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS historical_data_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        metadata = {
            "source_url": source,
            "source_commit": SOURCE_COMMIT,
            "source_rows": str(total_source_rows),
            "accepted_rows": str(row_count),
            "rejected_rows": str(total_rejected_rows),
            "ticker_count": str(ticker_count),
            "minimum_date": str(minimum_date),
            "maximum_date": str(maximum_date),
        }
        connection.executemany(
            "INSERT OR REPLACE INTO historical_data_metadata (key, value) "
            "VALUES (?, ?)",
            metadata.items(),
        )

    return {
        "source_rows": total_source_rows,
        "accepted_rows": row_count,
        "rejected_rows": total_rejected_rows,
        "tickers": ticker_count,
        "minimum_date": minimum_date,
        "maximum_date": maximum_date,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the prototype NGX historical dataset."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="CSV path or URL (default: pinned public GitHub dataset)",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"Temporary SQLite output (default: {DEFAULT_DATABASE})",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    summary = import_historical_data(arguments.source, arguments.database)
    print(
        "Imported {accepted_rows:,} historical rows for {tickers} tickers "
        "({minimum_date} to {maximum_date}); rejected {rejected_rows:,} rows."
        .format(**summary)
    )
    print(f"Temporary historical database: {arguments.database.resolve()}")


if __name__ == "__main__":
    main()
