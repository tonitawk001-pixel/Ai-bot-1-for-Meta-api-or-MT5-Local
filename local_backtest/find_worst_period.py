"""Analyze 5-year gold data to find the strongest 3-month uptrend (worst case for sell-biased strategy)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Load daily data
df = pd.read_csv(os.path.join(DATA_DIR, "XAUUSD_5y_D1.csv"), index_col=0, parse_dates=True)
df.columns = [c.lower() for c in df.columns]
df = df.sort_index()
close = df["close"]

print("=" * 70)
print("  FINDING WORST 3-MONTH PERIOD FOR SELL-BIASED STRATEGY")
print("  (Strongest gold uptrend = worst for our sell-biased bot)")
print("=" * 70)

# Scan rolling 63-day windows (~3 months of trading days)
best_return = -999
best_period = None
worst_return = 999
worst_period = None

windows = []
for i in range(63, len(close)):
    start = close.index[i - 63]
    end = close.index[i]
    pct = (close.iloc[i] / close.iloc[i - 63] - 1) * 100
    volatility = close.iloc[i-63:i+1].pct_change().std() * 100
    windows.append((start, end, pct, volatility))
    
    if pct > best_return:
        best_return = pct
        best_period = (start, end)
    if pct < worst_return:
        worst_return = pct
        worst_period = (start, end)

# Print top 5 strongest uptrends (worst for sell strategy)
print(f"\nTOP 5 STRONGEST UPTRENDS (WORST FOR SELL BIAS):")
print(f"{'Period':<30} {'Return':>10} {'Volatility':>12}")
print("-" * 55)
sorted_windows = sorted(windows, key=lambda x: -x[2])
for start, end, pct, vol in sorted_windows[:10]:
    label = f"{start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')}"
    print(f"{label:<30} {pct:>+8.2f}%   σ={vol:.2f}%")

print(f"\nTOP 5 STRONGEST DOWNTRENDS (BEST CASE):")
for start, end, pct, vol in sorted_windows[-5:]:
    label = f"{start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')}"
    print(f"{label:<30} {pct:>+8.2f}%   σ={vol:.2f}%")

print(f"\nOVERALL:")
print(f"  Best uptrend:   {best_period[0].strftime('%Y-%m-%d')} -> {best_period[1].strftime('%Y-%m-%d')} ({best_return:+.2f}%)")
print(f"  Best downtrend: {worst_period[0].strftime('%Y-%m-%d')} -> {worst_period[1].strftime('%Y-%m-%d')} ({worst_return:+.2f}%)")