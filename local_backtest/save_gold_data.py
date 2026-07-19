"""
Save Historical Gold Data (XAUUSD) to Local Files
=================================================
Downloads multi-period gold data from Yahoo Finance and saves as CSV files
for use in backtests without re-downloading.

Outputs (in local_backtest/data/):
    - XAUUSD_60d_M5.csv        (60 days, 5-minute candles)
    - XAUUSD_60d_M15.csv       (60 days, 15-minute candles)
    - XAUUSD_2y_H1.csv         (2 years, hourly candles)
    - XAUUSD_5y_D1.csv         (5 years, daily candles)
    - data_info.txt            (metadata about each file)

Usage:
    python save_gold_data.py
"""

import os
import sys
import time
from datetime import datetime

import yfinance as yf
import pandas as pd


# === Configuration ===
SYMBOL = "GC=F"  # Gold futures (most liquid on Yahoo)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def fix_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names (yfinance sometimes uses MultiIndex)."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df


def fetch_and_save(symbol: str, interval: str, period: str, filename: str, label: str):
    """Fetch data from yfinance and save as CSV."""
    print(f"\n[{label}] Fetching {symbol} {interval} for {period}...")
    try:
        df = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            progress=False,
        )
        if df.empty:
            print(f"  [!] No data returned for {label}")
            return None

        df = fix_columns(df)
        df = df.dropna()

        # Add metadata columns
        df["symbol"] = symbol
        df["interval"] = interval

        # Save
        output_path = os.path.join(DATA_DIR, filename)
        df.to_csv(output_path)
        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        print(f"  [+] Saved: {filename}")
        print(f"      Candles: {len(df)}")
        print(f"      Period:  {df.index[0]} -> {df.index[-1]}")
        print(f"      Size:    {size_mb:.2f} MB")
        return df

    except Exception as exc:
        print(f"  [!] Error fetching {label}: {exc}")
        return None


def main():
    print("=" * 60)
    print("  SAVING HISTORICAL GOLD DATA (XAUUSD / GC=F)")
    print("=" * 60)
    print(f"Output directory: {DATA_DIR}")

    os.makedirs(DATA_DIR, exist_ok=True)

    summaries = []

    # 1. 60 days of M5 (5-minute) candles
    df_m5 = fetch_and_save(
        symbol=SYMBOL, interval="5m", period="60d",
        filename="XAUUSD_60d_M5.csv",
        label="M5 (5-min, 60 days)",
    )
    if df_m5 is not None:
        summaries.append({
            "file": "XAUUSD_60d_M5.csv",
            "interval": "5m",
            "period": "60d",
            "candles": len(df_m5),
            "from": str(df_m5.index[0]),
            "to": str(df_m5.index[-1]),
        })

    # 2. 60 days of M15 (15-minute) candles
    df_m15 = fetch_and_save(
        symbol=SYMBOL, interval="15m", period="60d",
        filename="XAUUSD_60d_M15.csv",
        label="M15 (15-min, 60 days)",
    )
    if df_m15 is not None:
        summaries.append({
            "file": "XAUUSD_60d_M15.csv",
            "interval": "15m",
            "period": "60d",
            "candles": len(df_m15),
            "from": str(df_m15.index[0]),
            "to": str(df_m15.index[-1]),
        })

    # 3. 2 years of H1 (1-hour) candles
    df_h1 = fetch_and_save(
        symbol=SYMBOL, interval="1h", period="2y",
        filename="XAUUSD_2y_H1.csv",
        label="H1 (1-hour, 2 years)",
    )
    if df_h1 is not None:
        summaries.append({
            "file": "XAUUSD_2y_H1.csv",
            "interval": "1h",
            "period": "2y",
            "candles": len(df_h1),
            "from": str(df_h1.index[0]),
            "to": str(df_h1.index[-1]),
        })

    # 4. 5 years of D1 (daily) candles
    df_d1 = fetch_and_save(
        symbol=SYMBOL, interval="1d", period="5y",
        filename="XAUUSD_5y_D1.csv",
        label="D1 (daily, 5 years)",
    )
    if df_d1 is not None:
        summaries.append({
            "file": "XAUUSD_5y_D1.csv",
            "interval": "1d",
            "period": "5y",
            "candles": len(df_d1),
            "from": str(df_d1.index[0]),
            "to": str(df_d1.index[-1]),
        })

    # Write metadata file
    info_path = os.path.join(DATA_DIR, "data_info.txt")
    with open(info_path, "w") as f:
        f.write("XAUUSD Historical Data (GC=F Gold Futures)\n")
        f.write(f"Source: Yahoo Finance\n")
        f.write(f"Symbol: {SYMBOL}\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"\n{'='*60}\n")
        f.write("FILES:\n\n")
        for s in summaries:
            f.write(f"  {s['file']}\n")
            f.write(f"    Interval: {s['interval']}\n")
            f.write(f"    Period:   {s['period']}\n")
            f.write(f"    Candles:  {s['candles']:,}\n")
            f.write(f"    From:     {s['from']}\n")
            f.write(f"    To:       {s['to']}\n\n")

    print()
    print("=" * 60)
    print("  ALL FILES SAVED SUCCESSFULLY")
    print("=" * 60)
    for s in summaries:
        print(f"  {s['file']:<28}  {s['candles']:>7,} candles  ({s['interval']})")
    print()
    print(f"  Metadata: {info_path}")
    print(f"  Directory: {DATA_DIR}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
