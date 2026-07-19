"""Download worst-case period data using H1 data (works historically), resample to M15."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SYMBOL = "GC=F"

def fix_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df

def resample_h1_to_m15(df_h1):
    """Resample 1h data to 15min using linear interpolation."""
    idx = pd.date_range(start=df_h1.index[0], end=df_h1.index[-1] + pd.Timedelta(hours=1), freq='15min')
    idx = idx[idx < df_h1.index[-1] + pd.Timedelta(hours=1)]
    
    df_m15 = pd.DataFrame(index=idx, columns=['open', 'high', 'low', 'close', 'volume'])
    
    for col in ['open', 'high', 'low', 'close']:
        df_m15[col] = np.nan
        df_m15.loc[df_h1.index, col] = df_h1[col].values
        df_m15[col] = df_m15[col].interpolate(method='linear')
    
    # Volume - forward fill
    df_m15['volume'] = np.nan
    df_m15.loc[df_h1.index, 'volume'] = df_h1['volume'].values
    df_m15['volume'] = df_m15['volume'].fillna(0)
    
    # High/low should account for interpolated values
    df_m15['high'] = df_m15[['open', 'close']].max(axis=1)
    df_m15['low'] = df_m15[['open', 'close']].min(axis=1)
    
    return df_m15

print("=" * 60)
print("  DOWNLOADING WORST-CASE PERIOD DATA")
print("  Period: Oct 28, 2025 - Jan 29, 2026 (+34% uptrend)")
print("=" * 60)

# Download H1 data for extended period
print("\n[H1] Downloading hourly data Sep 2025 - Feb 2026...")
df_h1 = yf.download(
    tickers=SYMBOL,
    interval="1h",
    start="2025-09-01",
    end="2026-03-01",
    progress=True,
)

if df_h1 is not None and not df_h1.empty:
    df_h1 = fix_columns(df_h1)
    df_h1 = df_h1.dropna()
    print(f"  [+] Got {len(df_h1)} hourly candles")
    print(f"      Period: {df_h1.index[0]} -> {df_h1.index[-1]}")
    
    # Save raw H1
    df_h1.to_csv(os.path.join(DATA_DIR, "XAUUSD_worst_H1.csv"))
    
    # Resample to M15
    print("\n   Resampling H1 to M15...")
    df_m15 = resample_h1_to_m15(df_h1)
    
    # Also create M5 from M15 (just forward fill)
    idx_m5 = pd.date_range(start=df_m15.index[0], end=df_m15.index[-1] + pd.Timedelta(minutes=15), freq='5min')
    idx_m5 = idx_m5[idx_m5 < df_m15.index[-1] + pd.Timedelta(minutes=15)]
    
    df_m5 = pd.DataFrame(index=idx_m5, columns=['open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close']:
        # Forward fill M15 values to M5
        df_m5[col] = np.nan
        for m15_time in df_m15.index:
            mask = (df_m5.index >= m15_time) & (df_m5.index < m15_time + pd.Timedelta(minutes=15))
            df_m5.loc[mask, col] = df_m15.loc[m15_time, col]
        # Fill any remaining NaN
        df_m5[col] = df_m5[col].ffill()
    
    df_m5['volume'] = 0
    
    # Save
    m15_path = os.path.join(DATA_DIR, "XAUUSD_worst_M15.csv")
    m5_path = os.path.join(DATA_DIR, "XAUUSD_worst_M5.csv")
    df_m15.to_csv(m15_path)
    df_m5.to_csv(m5_path)
    
    print(f"\n  ✅ M15 saved: {len(df_m15)} candles")
    print(f"     Period: {df_m15.index[0]} -> {df_m15.index[-1]}")
    print(f"  ✅ M5 saved: {len(df_m5)} candles")
    print(f"     Period: {df_m5.index[0]} -> {df_m5.index[-1]}")
else:
    print("  [!] Failed to download data")

print("\nDone!")