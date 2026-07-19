"""Download M5 and M15 data for worst-case period: Oct 2025 - Feb 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SYMBOL = "GC=F"
os.makedirs(DATA_DIR, exist_ok=True)

def fix_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df

print("=" * 60)
print("  DOWNLOADING M5 & M15 DATA FOR WORST-CASE PERIOD")
print("  Gold uptrend: Oct 2025 - Feb 2026 (+34%)")
print("=" * 60)

# Download M15 data - need Oct 2025 to Feb 2026
# Use extended period to ensure enough warmup data
for interval, label in [("15m", "M15"), ("5m", "M5")]:
    print(f"\n[{label}] Downloading {interval}...")
    try:
        df = yf.download(
            tickers=SYMBOL,
            interval=interval,
            start="2025-09-01",  # Extra month for warmup (EMA200 needs 200 candles)
            end="2026-03-01",
            progress=True,
        )
        if df.empty:
            print(f"  [!] No data for {label}")
            continue
        df = fix_columns(df)
        df = df.dropna()
        fname = f"XAUUSD_worst_{label}.csv"
        df.to_csv(os.path.join(DATA_DIR, fname))
        print(f"  [+] Saved: {fname}")
        print(f"      Candles: {len(df)}")
        print(f"      Period:  {df.index[0]} -> {df.index[-1]}")
    except Exception as e:
        print(f"  [!] Error: {e}")

print("\nDone!")