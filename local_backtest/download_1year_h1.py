"""Download 1 year of H1 gold data for backtesting."""
import yfinance as yf
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SYMBOL = "GC=F"

print("=" * 60)
print("  DOWNLOADING 1 YEAR OF H1 GOLD DATA")
print("=" * 60)

df_h1 = yf.download(SYMBOL, interval="1h", start="2025-07-01", end="2026-07-16", progress=True)

if df_h1 is not None and not df_h1.empty:
    # Fix columns
    if isinstance(df_h1.columns, pd.MultiIndex):
        df_h1.columns = [c[0] for c in df_h1.columns]
    df_h1 = df_h1.rename(columns=str.lower)
    df_h1 = df_h1.dropna()

    # Save
    path = os.path.join(DATA_DIR, "XAUUSD_1y_H1.csv")
    df_h1.to_csv(path)
    print(f"  [+] Saved: {len(df_h1)} candles")
    print(f"      From: {df_h1.index[0]}")
    print(f"      To:   {df_h1.index[-1]}")
else:
    print("  [!] Failed to download data")