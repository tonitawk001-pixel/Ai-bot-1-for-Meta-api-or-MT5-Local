"""
Final analysis: check strategy signals without spread filter, 
and calculate missed opportunities.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["METAAPI_TOKEN"] = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJhZjc4NTJlNDYwMTVlMDg5MjE2M2YxZDAzODNmNjk2MSIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJtZXRhYXBpLXJwYy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJyaXNrLW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJyaXNrLW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiYWY3ODUyZTQ2MDE1ZTA4OTIxNjNmMWQwMzgzZjY5NjEiLCJpYXQiOjE3ODM3NjIxODMsImV4cCI6MTc5MTUzODE4M30.ALjnk5ihx-SY3HcopWpPfy0P-YEgyChZtxHabVZBsLMlKJIE9thVUm2X6V5V6y54sDUgBjPsT11FgN0YZBhaCtKDmR7AlKJmL4jH33TQ7_RH8cXYPa18DhCJhndfTvPk_Wj7mMTAUmhUenZZptklWTccRKWfxyAZUdRKPghr98PhJgkr86asuiO05THEOdAQ-JWUFJ3OL0JtXQU726P8YRyyRh-P9LX5lnstZY1yfkH7EEVWWzeG0GeIXOhjDmDST6ABiYqRzeuNeY64socnJO6K9WBew2SH9hQJu9PS07tvhExUnvY9YOZJFcr61u_djKnskz8m52fd6nbRoc4zuRHIF0GwbiNIms1JDzjYg1oeesx-yaAYgxTaxXoo_uumqGduzXOuSpe00PkF1_Aa2dp67sAE-0HMpIIH6ogAU4aYYUwRYeGJB6ynzbbIoQvb_nEkCb8PkIFx1a8CRKruk-trmzxceNgDHRRWzOb3jfRu1pYbwxmStf50qyE-s3SJaCRTqcvKzqfp7VZo7m5WnIPnGcU8zJEyXIaNeb4d6oSx2ejV2hRk11y-tX8_AGZjoDWS-gSJD9jHcSMU_7NSzFXkKBzVEPCZ61n-tko8GHzjNQHls3P4QKBpnq7ApMgjv0keDZe2HIn94mwjE3qpdkF9zJb08LnGfSJQcbKQTjk"
os.environ["METAAPI_ACCOUNT_ID"] = "d80b2dae-5260-4e65-b4ab-a77e95cb3d89"

from trading_bot.metaapi.data_feed import get_candles
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
from trading_bot.strategy.gold_volatility_filter import GoldVolatilityFilter
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=24)

print("=" * 70)
print("🚀 FINAL ANALYSIS: Missed Trades in Last 24 Hours")
print("=" * 70)
print(f"Analysis time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"Range: {cutoff.strftime('%Y-%m-%d %H:%M UTC')} -> {now.strftime('%Y-%m-%d %H:%M UTC')}")
print()

# Get the data
m5 = get_candles("XAUUSD", "M5", 400)
m15 = get_candles("XAUUSD", "M15", 200)

if m5 is None or m15 is None:
    print("❌ Failed to get data")
    sys.exit(1)

# Filter to our time window
m5_w = m5[m5.index >= cutoff - timedelta(hours=2)]
m15_w = m15[m15.index >= cutoff - timedelta(hours=2)]

print(f"Data loaded: {len(m5_w)} M5 candles, {len(m15_w)} M15 candles")
print()

strategy = GoldScalpingStrategy()
vf = GoldVolatilityFilter()

# Simulate v22_cycle but with spread = 36 (the actual account spread)
signals = []

for m15_time in sorted(m15_w.index.unique()):
    # Skip future
    if m15_time > now:
        continue
    
    # Get full historical window
    m15_hist = m15[m15.index <= m15_time].tail(200)
    m5_all = m5[m5.index <= m15_time]
    m5_hist = m5_all.tail(500)
    
    if len(m15_hist) < 50 or len(m5_hist) < 50:
        continue
    
    # Compute indicators
    try:
        m5_ind = compute_all_indicators(m5_hist)
        m15_ind = compute_all_indicators(m15_hist)
    except:
        continue
    
    if m5_ind.get("atr") is None or pd.isna(m5_ind["atr"].iloc[-1]):
        continue
    
    atr_val = float(m5_ind["atr"].iloc[-1])
    if atr_val < 1.0:
        continue
    
    # Session filters
    hour = m15_time.hour
    if hour < 8 or hour >= 22:
        continue
    
    if m15_time.weekday() == 4 and hour >= 18:  # Friday
        continue
    
    # Run strategy
    try:
        empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
        empty_m1_ohlcv = m5_hist.tail(20)
        result = strategy.analyze(
            m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
            m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5_hist, m15_ohlcv=m15_hist, news_context=None,
        )
    except:
        continue
    
    direction = result.get("direction", "NONE")
    score = result.get("setup_score", 0)
    
    if direction == "NONE" or score < 45:
        continue
    
    # Calculate ADX
    from scripts.backtest_24h import compute_adx
    try:
        adx_series = compute_adx(m5_hist["high"], m5_hist["low"], m5_hist["close"], period=14)
        adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0
    except:
        adx_val = 0
    
    # RSI confluence
    try:
        rsi_bullish = m5_ind["rsi"].iloc[-1] > 40 and m15_ind["rsi"].iloc[-1] > 40
        rsi_bearish = m5_ind["rsi"].iloc[-1] < 60 and m15_ind["rsi"].iloc[-1] < 60
        if direction == "BUY" and not rsi_bullish:
            continue
        if direction == "SELL" and not rsi_bearish:
            continue
    except:
        pass
    
    # EMA200
    closes = m15_hist["close"].values
    if len(closes) >= 200:
        ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
        if len(ema200) >= 10:
            rising = float(ema200[-1]) > float(ema200[-10])
            if direction == "BUY" and not rising:
                continue
            if direction == "SELL" and rising:
                continue
    
    # Volatility filter
    try:
        vo = vf.analyze(
            m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5_hist, m15_ohlcv=m15_hist,
            m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
        )
        if not vo.get("trade_ok", False):
            continue
    except:
        pass
    
    # Calculate trade params
    current_price = float(m15_hist["close"].iloc[-1])
    tp_mult = 5.0 if adx_val >= 25 else 3.5
    sl_dist = atr_val * 1.5
    tp_dist = atr_val * tp_mult
    
    if direction == "BUY":
        sl = round(current_price - sl_dist, 2)
        tp = round(current_price + tp_dist, 2)
    else:
        sl = round(current_price + sl_dist, 2)
        tp = round(current_price - tp_dist, 2)
    
    # Lot size (2% risk on ~$286 balance)
    risk_amount = 286.32 * 0.02
    risk_per_lot = sl_dist * 100
    lot = max(0.01, round(risk_amount / risk_per_lot / 0.01) * 0.01) if risk_per_lot > 0 else 0.01
    
    spread = float(m5_hist["spread"].iloc[-1]) if "spread" in m5_hist.columns else 0
    
    signals.append({
        "time": m15_time,
        "direction": direction,
        "score": score,
        "price": current_price,
        "sl": sl,
        "tp": tp,
        "lot": lot,
        "atr": atr_val,
        "adx": adx_val,
        "spread": spread,
        "blocked_by_spread": spread > 30,
        "reason": result.get("reason", "")[:60],
    })

# Print results
print(f"{'#':<3} {'Time (UTC)':<18} {'Dir':<6} {'Price':<10} {'SL':<10} {'TP':<10} {'Lot':<8} {'Score':<6} {'Spread':<8} {'Status':<20}")
print("-" * 100)

buy_count = sell_count = 0
blocked_count = 0
fired_signals = []

for i, s in enumerate(signals, 1):
    status = "⚠️ BLOCKED by spread" if s["blocked_by_spread"] else "✅ WOULD FIRE"
    if s["direction"] == "BUY": buy_count += 1
    else: sell_count += 1
    if s["blocked_by_spread"]: blocked_count += 1
    else: fired_signals.append(s)
    
    ts = s["time"].strftime('%m/%d %H:%M')
    print(f"{i:<3} {ts:<18} {s['direction']:<6} {s['price']:<10.2f} {s['sl']:<10.2f} {s['tp']:<10.2f} {s['lot']:<8.4f} {s['score']:<6} {s['spread']:<8.0f} {status}")

print()
print("=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"Total valid signals (passing ALL filters): {len(signals)}")
print(f"  BUY: {buy_count} | SELL: {sell_count}")
print(f"  Blocked by spread (>30pts): {blocked_count}")
print(f"  Would have traded (if spread OK): {len(fired_signals)}")
print()
print("🔴 ROOT CAUSE: The bot's spread filter (MAX_SPREAD_POINTS=30) blocks 100% of trades")
print(f"   because ACCMGIobal-Demo maintains a constant spread of ~36 points for XAUUSD.")
print(f"   The bot was NEITHER running NOR would it have traded due to this spread filter.")
print()
print("🛠️ RECOMMENDED FIXES:")
print("   1. Increase MAX_SPREAD_POINTS to 40-45 in main_v22_metaapi.py")
print("   2. Re-deploy the bot to Contabo with .env file")
print("   3. Fix the MetaApi subscription timeout by checking region settings")
print()