"""Download M5/M15 data in 60-day chunks to cover worst-case period."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SYMBOL = "GC=F"
os.makedirs(DATA_DIR, exist_ok=True)

def fix_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df

print("=" * 60)
print("  DOWNLOADING HISTORICAL M5 & M15 DATA IN 60-DAY CHUNKS")
print("=" * 60)

# Download in overlapping 60-day periods
# Yahoo only gives last 60 days for minute data, but we can use the period parameter
end_dates = ["2026-01-15", "2025-11-15", "2025-09-15"]  # rolling backwards

all_m5 = []
all_m15 = []

for end_date_str in end_dates:
    for interval, label, all_list in [("15m", "M15", all_m15), ("5m", "M5", all_m5)]:
        print(f"\n[{label}] Downloading 60 days ending {end_date_str}...")
        try:
            # Use period parameter instead of start/end for minute data
            df = yf.download(
                tickers=SYMBOL,
                interval=interval,
                period="60d",
                end=end_date_str,
                progress=True,
            )
            if df is not None and not df.empty:
                df = fix_columns(df)
                df = df.dropna()
                all_list.append(df)
                print(f"  [+] Got {len(df)} candles: {df.index[0]} -> {df.index[-1]}")
            else:
                print(f"  [!] Empty for {label} ending {end_date_str}")
        except Exception as e:
            print(f"  [!] Error: {e}")

# Try one more approach - use rolling download with explicit date ranges
print("\n\n=== Trying alternative approach with date ranges ===")
for interval, label, all_list in [("15m", "M15", all_m15), ("5m", "M5", all_m5)]:
    # Download starting from Oct 2025 going forward
    for start_str in ["2025-10-01", "2025-11-01", "2025-12-01", "2026-01-01"]:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d")
        end_dt = start_dt + timedelta(days=60)
        print(f"\n[{label}] Trying {start_str} to {end_dt.strftime('%Y-%m-%d')}...")
        try:
            df = yf.download(
                tickers=SYMBOL,
                interval=interval,
                start=start_str,
                end=end_dt.strftime("%Y-%m-%d"),
                progress=False,
            )
            if df is not None and not df.empty:
                df = fix_columns(df)
                df = df.dropna()
                all_list.append(df)
                print(f"  [+] Got {len(df)} candles: {df.index[0]} -> {df.index[-1]}")
            else:
                print(f"  [!] Empty")
        except Exception as e:
            print(f"  [!] Error: {e}")

# Combine and save
if all_m15:
    combined_m15 = pd.concat(all_m15)
    combined_m15 = combined_m15[~combined_m15.index.duplicated(keep='last')].sort_index()
    combined_m15.to_csv(os.path.join(DATA_DIR, "XAUUSD_worst_M15.csv"))
    print(f"\n✅ M15 combined: {len(combined_m15)} candles, {combined_m15.index[0]} -> {combined_m15.index[-1]}")

if all_m5:
    combined_m5 = pd.concat(all_m5)
    combined_m5 = combined_m5[~combined_m5.index.duplicated(keep='last')].sort_index()
    combined_m5.to_csv(os.path.join(DATA_DIR, "XAUUSD_worst_M5.csv"))
    print(f"✅ M5 combined: {len(combined_m5)} candles, {combined_m5.index[0]} -> {combined_m5.index[-1]}")

print("\nDone!")