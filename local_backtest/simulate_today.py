"""Simulate the bot on today's gold market data to see what signals fire."""
import os, sys, warnings
from datetime import datetime, timedelta, timezone
from dateutil import parser
warnings.filterwarnings("ignore")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import yfinance as yf
import pandas as pd
import numpy as np

from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy

SYMBOL = "XAUUSD"
STARTING_BALANCE = 297.07
MIN_SCORE = 45
MAX_POSITIONS = 1
MIN_ATR = 1.0
TP_ATR_MULT = 3.5
SL_ATR_MULT = 1.5
BE_ATR_MULT = 2.0
TRAIL_ATR_MULT = 0.7
HALT_AFTER_LOSSES = 3
HALT_HOURS = 6
ENTRY_COOLDOWN_MINUTES = 30
DAILY_LOSS_PCT = 0.03
SPREAD_PIPS = 0.50
TRADE_HOURS_START = 8
TRADE_HOURS_END = 22

# Download today's data (last 24h)
print("=" * 70)
print("  TODAY'S GOLD MARKET SIMULATION")
print("  Running the bot against live data to see what signals fire")
print("=" * 70)

def fix_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df

# Download M15 data (last 7 days for warmup + today)
print("\n[1/3] Downloading today's gold data...")
df_m15 = yf.download("GC=F", interval="15m", period="7d", progress=False)
df_m5 = yf.download("GC=F", interval="5m", period="7d", progress=False)

if df_m15 is None or df_m15.empty or df_m5 is None or df_m5.empty:
    print("Failed to download data. Check internet.")
    sys.exit(1)

df_m15 = fix_columns(df_m15).dropna()
df_m5 = fix_columns(df_m5).dropna()

# Normalize to UTC
df_m15.index = pd.to_datetime(df_m15.index, utc=True)
df_m5.index = pd.to_datetime(df_m5.index, utc=True)

# Filter to today (July 15) and yesterday for warmup
today_start = "2026-07-14"
today_end = "2026-07-16"

d15 = df_m15[(df_m15.index >= today_start) & (df_m15.index < today_end)].copy()
d5 = df_m5[(df_m5.index >= today_start) & (df_m5.index < today_end)].copy()

print(f"M15: {len(d15)} candles, {d15.index[0].strftime('%H:%M UTC')} -> {d15.index[-1].strftime('%H:%M UTC')}")
print(f"M5:  {len(d5)} candles")

# Run simulation
print("\n[2/3] Running strategy on today's data...")
strategy = GoldScalpingStrategy()
strategy._max_trades_per_day = 50
strategy._max_open_positions = MAX_POSITIONS

signals_found = []
last_entry = None

# Start from index 200 to have enough warmup data
for i in range(min(200, len(d15)-1), len(d15)):
    ct = d15.index[i]
    price = float(d15["close"].iloc[i])
    
    # Session filter
    if not (TRADE_HOURS_START <= ct.hour < TRADE_HOURS_END):
        continue
    
    m15w = d15.iloc[max(0,i-499):i+1].copy()
    m5u = d5[d5.index <= ct]
    m5w = m5u.tail(500).copy()
    
    if len(m15w) < 50 or len(m5w) < 50:
        continue
    
    m5_ind = compute_all_indicators(m5w)
    m15_ind = compute_all_indicators(m15w)
    if m5_ind is None or m15_ind is None:
        continue
    if m5_ind.get("atr") is None or len(m5_ind["atr"]) == 0:
        continue
    
    atr_val = float(m5_ind["atr"].iloc[-1])
    if atr_val < MIN_ATR:
        continue
    if last_entry and (ct - last_entry).total_seconds() / 60 < ENTRY_COOLDOWN_MINUTES:
        continue
    
    try:
        empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
        eo = m5w.tail(20)
        result = strategy.analyze(
            m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
            m1_ohlcv=eo, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None,
        )
    except:
        continue
    
    direction = result.get("direction", "NONE")
    score = result.get("setup_score", 0)
    if direction == "NONE" or score < MIN_SCORE:
        continue
    
    # RSI filter
    try:
        rsi5 = m5_ind["rsi"].iloc[-1]
        rsi15 = m15_ind["rsi"].iloc[-1]
        if direction == "BUY" and not (rsi5 > 40 and rsi15 > 40):
            continue
        if direction == "SELL" and not (rsi5 < 60 and rsi15 < 60):
            continue
    except:
        pass
    
    # EMA200 filter
    closes = m15w["close"].values
    if len(closes) >= 200:
        ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
        if len(ema200) >= 10:
            rising = float(ema200[-1]) > float(ema200[-10])
            if direction == "BUY" and not rising:
                continue
            if direction == "SELL" and rising:
                continue
    
    # This is a valid signal!
    sl_dist = atr_val * SL_ATR_MULT
    tp_dist = atr_val * TP_ATR_MULT
    if direction == "BUY":
        sl = round(price - sl_dist, 2)
        tp = round(price + tp_dist, 2)
    else:
        sl = round(price + sl_dist, 2)
        tp = round(price - tp_dist, 2)
    
    bt = price + (atr_val * BE_ATR_MULT if direction == "BUY" else -atr_val * BE_ATR_MULT)
    
    signals_found.append({
        "time": ct,
        "direction": direction,
        "score": score,
        "price": price,
        "sl": sl,
        "tp": tp,
        "atr": round(atr_val, 2),
        "be_target": round(bt, 2),
        "rsi_m5": round(rsi5, 1) if 'rsi5' in dir() else None,
        "rsi_m15": round(rsi15, 1) if 'rsi15' in dir() else None,
    })
    last_entry = ct

print(f"\n[3/3] Results: {len(signals_found)} signals found\n")

if not signals_found:
    print("  ❌ NO TRADES WOULD HAVE BEEN OPENED TODAY")
    print("  Reason: Filters are blocking all signals")
    print("\n  Possible reasons:")
    print("  - Gold is not trending strongly enough")
    print("  - EMA200 slope conflicts with direction")
    print("  - RSI is not in confluence zone")
    print("  - Volatility (ATR) too low")
else:
    print(f"  {'Time (Beirut)':<20} {'Dir':<6} {'Score':<8} {'Price':<10} {'SL':<10} {'TP':<10} {'ATR':<8} {'RSI M5':<8} {'RSI M15':<8}")
    print(f"  {'-'*88}")
    for s in signals_found:
        beirut = s['time'].tz_convert('Asia/Beirut') if hasattr(s['time'], 'tz_convert') else s['time']
        label = beirut.strftime('%H:%M %Z') if hasattr(beirut, 'strftime') else str(beirut)
        rs5 = str(s.get('rsi_m5', '?'))
        rs15 = str(s.get('rsi_m15', '?'))
        print(f"  {label:<20} {s['direction']:<6} {s['score']:<8} {s['price']:<10.2f} {s['sl']:<10.2f} {s['tp']:<10.2f} {s['atr']:<8} {rs5:<8} {rs15:<8}")
    
    print(f"\n  🎯 {len(signals_found)} valid signals would have been executed")
    print(f"  First signal: {signals_found[0]['time'].strftime('%H:%M UTC')}")
    print(f"  Last signal:  {signals_found[-1]['time'].strftime('%H:%M UTC')}")

print("\n" + "=" * 70)
print("  SIMULATION COMPLETE")
print("=" * 70)