"""Analyze spread data from MetaApi to understand why trades were blocked."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["METAAPI_TOKEN"] = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJhZjc4NTJlNDYwMTVlMDg5MjE2M2YxZDAzODNmNjk2MSIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJtZXRhYXBpLXJwYy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJyaXNrLW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJyaXNrLW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiYWY3ODUyZTQ2MDE1ZTA4OTIxNjNmMWQwMzgzZjY5NjEiLCJpYXQiOjE3ODM3NjIxODMsImV4cCI6MTc5MTUzODE4M30.ALjnk5ihx-SY3HcopWpPfy0P-YEgyChZtxHabVZBsLMlKJIE9thVUm2X6V5V6y54sDUgBjPsT11FgN0YZBhaCtKDmR7AlKJmL4jH33TQ7_RH8cXYPa18DhCJhndfTvPk_Wj7mMTAUmhUenZZptklWTccRKWfxyAZUdRKPghr98PhJgkr86asuiO05THEOdAQ-JWUFJ3OL0JtXQU726P8YRyyRh-P9LX5lnstZY1yfkH7EEVWWzeG0GeIXOhjDmDST6ABiYqRzeuNeY64socnJO6K9WBew2SH9hQJu9PS07tvhExUnvY9YOZJFcr61u_djKnskz8m52fd6nbRoc4zuRHIF0GwbiNIms1JDzjYg1oeesx-yaAYgxTaxXoo_uumqGduzXOuSpe00PkF1_Aa2dp67sAE-0HMpIIH6ogAU4aYYUwRYeGJB6ynzbbIoQvb_nEkCb8PkIFx1a8CRKruk-trmzxceNgDHRRWzOb3jfRu1pYbwxmStf50qyE-s3SJaCRTqcvKzqfp7VZo7m5WnIPnGcU8zJEyXIaNeb4d6oSx2ejV2hRk11y-tX8_AGZjoDWS-gSJD9jHcSMU_7NSzFXkKBzVEPCZ61n-tko8GHzjNQHls3P4QKBpnq7ApMgjv0keDZe2HIn94mwjE3qpdkF9zJb08LnGfSJQcbKQTjk"
os.environ["METAAPI_ACCOUNT_ID"] = "d80b2dae-5260-4e65-b4ab-a77e95cb3d89"

from trading_bot.metaapi.data_feed import get_candles
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
import pandas as pd
import numpy as np

# Get M5 data
m5 = get_candles("XAUUSD", "M5", 500)
if m5 is None or "spread" not in m5.columns:
    print("No spread data available")
    sys.exit(1)

spreads = m5["spread"].dropna()
recent = spreads.tail(288)

print("=" * 60)
print("📊 GOLD SPREAD ANALYSIS (Last 24h)")
print("=" * 60)
print(f"Total candles: {len(m5)}")
print(f"Spreads in last 24h: {len(recent)}")
print()
print(f"Spread Statistics:")
print(f"  Average: {recent.mean():.1f} points")
print(f"  Median:  {recent.median():.1f} points")
print(f"  Max:     {recent.max():.1f} points")
print(f"  Min:     {recent.min():.1f} points")
print(f"  Std Dev: {recent.std():.1f} points")
print()

print("Hourly Average Spread:")
hourly = m5.copy()
hourly["hour"] = hourly.index.hour
hourly_spread = hourly.groupby("hour")["spread"].mean()
for h in range(24):
    if h in hourly_spread.index:
        print(f"  {h:02d}:00 UTC: {hourly_spread[h]:.1f} points")
print()

print("Spread Distribution (last 24h):")
bins = [0, 10, 20, 30, 40, 50, 100, 200]
for i in range(len(bins)-1):
    count = len(recent[(recent >= bins[i]) & (recent < bins[i+1])])
    if count > 0:
        pct = count / len(recent) * 100
        bar = "#" * int(pct / 2)
        print(f"  {bins[i]:>3}-{bins[i+1]:>3} pts: {count:>3} candles ({pct:>4.1f}%) {bar}")

print()
# Check what percentage had spread <= 30 (the bot's limit)
ok = len(recent[recent <= 30])
print(f"Candles with spread <= 30 pts: {ok}/{len(recent)} ({ok/len(recent)*100:.1f}%)")
print(f"Candles with spread > 30 pts:  {len(recent) - ok}/{len(recent)} ({(len(recent)-ok)/len(recent)*100:.1f}%)")

# Show the most recent high-spread events
print()
print("Recent high-spread events (> 30 pts):")
high_spread = m5[m5["spread"] > 30].tail(10)
for idx, row in high_spread.iterrows():
    print(f"  {idx.strftime('%m/%d %H:%M')}: spread={row['spread']:.0f} close={row['close']:.2f}")

# Now run backtest WITHOUT spread filter to see if strategy would have fired
print()
print("=" * 60)
print("🎯 TRADE SIGNALS (Spread Filter REMOVED)")
print("=" * 60)

m5_last48 = m5.tail(300)
m15 = get_candles("XAUUSD", "M15", 200)
if m15 is not None:
    strategy = GoldScalpingStrategy()
    signals_found = []
    
    for idx in m15.index:
        m15w = m15[m15.index <= idx].tail(100)
        m5w = m5_last48[m5_last48.index <= idx].tail(300)
        
        if len(m15w) < 50 or len(m5w) < 50:
            continue
        
        try:
            m5_ind = compute_all_indicators(m5w)
            m15_ind = compute_all_indicators(m15w)
        except:
            continue
        
        if not m5_ind.get("atr") or pd.isna(m5_ind["atr"].iloc[-1]):
            continue
        
        atr_val = float(m5_ind["atr"].iloc[-1])
        if atr_val < 1.0:
            continue
        
        hour = idx.hour
        if hour < 8 or hour >= 22:
            continue
        
        # Run strategy (no spread filter)
        try:
            empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
            empty_m1_ohlcv = m5w.tail(20)
            result = strategy.analyze(
                m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
                m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None,
            )
        except:
            continue
        
        direction = result.get("direction", "NONE")
        score = result.get("setup_score", 0)
        
        if direction != "NONE" and score >= 45:
            current_price = float(m15w["close"].iloc[-1])
            spread_val = float(m5w["spread"].iloc[-1]) if "spread" in m5w.columns else 0
            signals_found.append({
                "time": idx,
                "direction": direction,
                "score": score,
                "price": current_price,
                "spread": spread_val,
                "atr": atr_val,
                "reason": result.get("reason", ""),
            })
    
    if signals_found:
        print(f"\nFound {len(signals_found)} trade signals (ignoring spread filter):")
        for s in signals_found:
            print(f"  {s['time'].strftime('%m/%d %H:%M')} | {s['direction']:<5} | Score: {s['score']:<3} | Price: {s['price']:<9.2f} | Spread: {s['spread']:.0f} pts | {s['reason'][:50]}")
        print()
        print("SIGNALS BLOCKED BY SPREAD FILTER ONLY:")
        blocked = [s for s in signals_found if s["spread"] > 30]
        print(f"  {len(blocked)} out of {len(signals_found)} signals would have been blocked by spread > 30")
        for s in blocked:
            print(f"  → {s['time'].strftime('%m/%d %H:%M')} {s['direction']} score={s['score']} spread={s['spread']:.0f}pts")
    else:
        print("No signals found even without spread filter")