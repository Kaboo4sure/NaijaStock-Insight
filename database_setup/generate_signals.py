from pathlib import Path
import sqlite3

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "naijastock.db"
HISTORICAL_DB_PATH = BASE_DIR / "historical_stock.db"


def table_exists(connection, table_name):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def load_stock_history():
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
        .drop(columns="source_priority")
        .reset_index(drop=True)
    )
    return stock_data


def calculate_rsi(close, length=14):
    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / length,
        adjust=False,
        min_periods=length,
    ).mean()
    average_loss = losses.ewm(
        alpha=1 / length,
        adjust=False,
        min_periods=length,
    ).mean()

    relative_strength = average_gain / average_loss.where(average_loss != 0)
    rsi = 100 - (100 / (1 + relative_strength))

    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_loss == 0) & (average_gain == 0), 50)
    return rsi


def calculate_macd(close, fast=12, slow=26, signal=9):
    fast_ema = close.ewm(
        span=fast,
        adjust=False,
        min_periods=fast,
    ).mean()
    slow_ema = close.ewm(
        span=slow,
        adjust=False,
        min_periods=slow,
    ).mean()

    macd = fast_ema - slow_ema
    macd_signal = macd.ewm(
        span=signal,
        adjust=False,
        min_periods=signal,
    ).mean()
    return macd, macd_signal


def generate_signals(dataframe):
    dataframe = dataframe.copy()
    dataframe.columns = dataframe.columns.str.lower()

    required_columns = [
        "date",
        "close",
        "volume",
        "ticker",
        "company_name",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    dataframe["date"] = pd.to_datetime(
        dataframe["date"],
        errors="coerce",
    )
    dataframe["close"] = pd.to_numeric(
        dataframe["close"],
        errors="coerce",
    )
    dataframe["volume"] = pd.to_numeric(
        dataframe["volume"],
        errors="coerce",
    )

    dataframe = dataframe.dropna(
        subset=["date", "close", "ticker"]
    )
    dataframe = dataframe.sort_values(["ticker", "date"])

    all_signals = []

    for ticker, group in dataframe.groupby("ticker"):
        group = group.copy()

        group["five_day_return"] = (
            group["close"].pct_change(5) * 100
        )
        group["rsi"] = calculate_rsi(group["close"])
        group["macd"], group["macdsignal"] = calculate_macd(
            group["close"]
        )

        group["twenty_day_avg_volume"] = (
            group["volume"].rolling(20, min_periods=20).mean()
        )
        group["volume_spike"] = (
            group["volume"] > group["twenty_day_avg_volume"]
        )

        group["signal_score"] = 0
        group.loc[
            (group["five_day_return"] > 0)
            & (group["rsi"] < 70)
            & (group["macd"] > group["macdsignal"])
            & group["volume_spike"],
            "signal_score",
        ] = 1

        weekly = (
            group.set_index("date")
            .resample("W-FRI")
            .last()
            .dropna(subset=["close"])
            .copy()
        )

        weekly["ticker"] = ticker
        weekly["company_name"] = group["company_name"].iloc[-1]
        weekly = weekly.reset_index()

        all_signals.append(
            weekly[
                [
                    "company_name",
                    "ticker",
                    "date",
                    "rsi",
                    "macd",
                    "five_day_return",
                    "signal_score",
                ]
            ]
        )

    if not all_signals:
        raise ValueError("No weekly signals could be generated.")

    result = (
        pd.concat(all_signals)
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )

    # Retain two years of website signals while calculating every indicator
    # from the full history first.
    latest_date = result["date"].max()
    result = result[
        result["date"] >= latest_date - pd.DateOffset(years=2)
    ].reset_index(drop=True)

    print(result.tail(10))
    return result


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    stock_data = load_stock_history()
    signal_data = generate_signals(stock_data)

    with sqlite3.connect(DB_PATH) as connection:
        signal_data.to_sql(
            "weekly_signals",
            connection,
            if_exists="replace",
            index=False,
        )

    print(
        f"Created weekly_signals with {len(signal_data)} rows "
        f"in {DB_PATH}"
    )


if __name__ == "__main__":
    main()
