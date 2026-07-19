"""
Backtest the bot for the last 24-48 hours to find missed trades.
Replays every M15 candle through the exact v22_cycle() logic.
"""
import os
import sys
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Force MetaAPI credentials from environment
if os.getenv("METAAPI_TOKEN") is None and os.getenv("METAAPI_ACCOUNT_ID") is None:
    print("⚠️  METAAPI_TOKEN or METAAPI_ACCOUNT_ID not found in .env!")
    print("Setting from script...")

# Ensure MetaAPI creds are set
os.environ.setdefault("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJhZjc4NTJlNDYwMTVlMDg5MjE2M2YxZDAzODNmNjk2MSIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfSx7ImlkIjoibWV0YWFwaS1yZXN0LWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJtZXRhYXBpLXJwYy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyJhY2NvdW50OiRVU0VSX0lEJDpkODBiMmRhZS01MjYwLTRlNjUtYjRhYi1hNzdlOTVjYjNkODkiXX0seyJpZCI6Im1ldGFzdGF0cy1hcGkiLCJtZXRob2RzIjpbIm1ldGFzdGF0cy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiYWNjb3VudDokVVNFUl9JRCQ6ZDgwYjJkYWUtNTI2MC00ZTY1LWI0YWItYTc3ZTk1Y2IzZDg5Il19LHsiaWQiOiJyaXNrLW1hbmFnZW1lbnQtYXBpIiwibWV0aG9kcyI6WyJyaXNrLW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiXSwicmVzb3VyY2VzIjpbImFjY291bnQ6JFVTRVJfSUQkOmQ4MGIyZGFlLTUyNjAtNGU2NS1iNGFiLWE3N2U5NWNiM2Q4OSJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiYWY3ODUyZTQ2MDE1ZTA4OTIxNjNmMWQwMzgzZjY5NjEiLCJpYXQiOjE3ODM3NjIxODMsImV4cCI6MTc5MTUzODE4M30.ALjnk5ihx-SY3HcopWpPfy0P-YEgyChZtxHabVZBsLMlKJIE9thVUm2X6V5V6y54sDUgBjPsT11FgN0YZBhaCtKDmR7AlKJmL4jH33TQ7_RH8cXYPa18DhCJhndfTvPk_Wj7mMTAUmhUenZZptklWTccRKWfxyAZUdRKPghr98PhJgkr86asuiO05THEOdAQ-JWUFJ3OL0JtXQU726P8YRyyRh-P9LX5lnstZY1yfkH7EEVWWzeG0GeIXOhjDmDST6ABiYqRzeuNeY64socnJO6K9WBew2SH9hQJu9PS07tvhExUnvY9YOZJFcr61u_djKnskz8m52fd6nbRoc4zuRHIF0GwbiNIms1JDzjYg1oeesx-yaAYgxTaxXoo_uumqGduzXOuSpe00PkF1_Aa2dp67sAE-0HMpIIH6ogAU4aYYUwRYeGJB6ynzbbIoQvb_nEkCb8PkIFx1a8CRKruk-trmzxceNgDHRRWzOb3jfRu1pYbwxmStf50qyE-s3SJaCRTqcvKzqfp7VZo7m5WnIPnGcU8zJEyXIaNeb4d6oSx2ejV2hRk11y-tX8_AGZjoDWS-gSJD9jHcSMU_7NSzFXkKBzVEPCZ61n-tko8GHzjNQHls3P4QKBpnq7ApMgjv0keDZe2HIn94mwjE3qpdkF9zJb08LnGfSJQcbKQTjk")
os.environ.setdefault("METAAPI_ACCOUNT_ID", "d80b2dae-5260-4e65-b4ab-a77e95cb3d89")

from trading_bot.utils.logger import logger
from trading_bot.metaapi.data_feed import get_candles
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
from trading_bot.strategy.gold_volatility_filter import GoldVolatilityFilter

# ============================================================
# Config (same as main_v22_metaapi.py)
# ============================================================
SYMBOL = "XAUUSD"
MIN_SCORE = 45
MAX_POSITIONS = 1
MIN_ATR = 1.0
TRADE_HOURS_START = 8
TRADE_HOURS_END = 22
HALT_AFTER_LOSSES = 3
HALT_HOURS = 6
ENTRY_COOLDOWN_MINUTES = 30
ADX_TREND_THRESHOLD = 25
MAX_SPREAD_POINTS = 30

# Results storage
backtest_signals = []


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Same ADX calculation as main_v22_metaapi.py"""
    if len(close) < period * 2:
        return pd.Series([np.nan] * len(close), index=close.index)
    high = high.astype(float); low = low.astype(float); close = close.astype(float)
    tr = pd.concat([(high - low).abs(), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    up_move = high - high.shift(); down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=close.index).ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=close.index).ewm(span=period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(span=period, adjust=False).mean()


def estimate_spread(m5_ohlcv: pd.DataFrame) -> float:
    """Estimate spread from ohlcv spread column."""
    if "spread" in m5_ohlcv.columns:
        spreads = m5_ohlcv["spread"].dropna()
        if len(spreads) > 0:
            return float(spreads.iloc[-1])
    # Default spread for gold ~20-30 points during active hours
    return 20.0


def simulate_missed_trade(direction: str, entry_price: float, atr_val: float, adx_val: float, timestamp):
    """Calculate what the trade would have been."""
    SL_ATR_MULT = 1.5
    TP_ATR_MULT = 3.5
    TP_ATR_MULT_TREND = 5.0
    
    tp_mult = TP_ATR_MULT_TREND if adx_val >= ADX_TREND_THRESHOLD else TP_ATR_MULT
    sl_dist = atr_val * SL_ATR_MULT
    tp_dist = atr_val * tp_mult
    
    if direction == "BUY":
        sl = round(entry_price - sl_dist, 2)
        tp = round(entry_price + tp_dist, 2)
    else:
        sl = round(entry_price + sl_dist, 2)
        tp = round(entry_price - tp_dist, 2)
    
    # Estimate profit at 2% risk on $288.92 balance
    risk_amount = 288.92 * 0.02  # $5.78
    risk_per_lot = sl_dist * 100
    lot = max(0.01, round(risk_amount / risk_per_lot / 0.01) * 0.01) if risk_per_lot > 0 else 0.01
    
    return {
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "lot": lot,
        "atr": atr_val,
        "adx": adx_val,
        "is_trend_tp": adx_val >= ADX_TREND_THRESHOLD,
        "estimated_risk": round(risk_amount, 2),
    }


def run_backtest(hours_back: int = 48):
    """Download data and replay through strategy for last N hours."""
    global backtest_signals
    backtest_signals = []
    
    print(f"\n{'='*70}")
    print(f"📊 BACKTESTING BOT STRATEGY FOR LAST {hours_back} HOURS")
    print(f"{'='*70}")
    print(f"Time now (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Symbol: {SYMBOL}")
    print(f"Min Score: {MIN_SCORE}")
    print(f"\nFetching M5 and M15 data from MetaApi...")
    
    # Fetch data
    m5_df = get_candles(symbol=SYMBOL, timeframe="M5", count=600)
    m15_df = get_candles(symbol=SYMBOL, timeframe="M15", count=500)
    
    if m5_df is None or m15_df is None:
        print("❌ Failed to fetch data!")
        return
    
    print(f"✅ M5: {len(m5_df)} candles ({m5_df.index[0]} -> {m5_df.index[-1]})")
    print(f"✅ M15: {len(m15_df)} candles ({m15_df.index[0]} -> {m15_df.index[-1]})")
    
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours_back)
    
    # Filter to last N hours
    m5_df = m5_df[m5_df.index >= cutoff - timedelta(hours=2)]  # +2h buffer for indicators
    m15_df = m15_df[m15_df.index >= cutoff - timedelta(hours=2)]
    
    print(f"Filtered M5: {len(m5_df)} candles (since {m5_df.index[0]})")
    print(f"Filtered M15: {len(m15_df)} candles (since {m15_df.index[0]})")
    print()
    
    # Initialize strategy (same as bot)
    strategy = GoldScalpingStrategy()
    strategy._max_trades_per_day = 50
    strategy._max_open_positions = MAX_POSITIONS
    
    vf = GoldVolatilityFilter()
    
    # Iterate through M15 candles (each M15 = 3 M5 candles)
    m15_iterations = sorted(m15_df.index.unique())
    first_pass = True
    trading_session_stats = {"signals": 0, "rejected_spread": 0, "rejected_news": 0, "rejected_rsi": 0, "rejected_ema": 0, "rejected_vol": 0, "rejected_score": 0, "rejected_cooldown": 0}
    
    print(f"{'Time (UTC)':<22} {'M15 Close':<12} {'Signal':<8} {'Score':<8} {'ATR':<8} {'ADX':<8} {'Reason':<40}")
    print("-" * 100)
    
    for m15_time in m15_iterations:
        # Skip if too far back
        if m15_time < cutoff:
            continue
        
        # Skip if in the future
        if m15_time > now:
            continue
        
        hour = m15_time.hour
        weekday = m15_time.weekday()  # Monday=0, Sunday=6
        
        # Get window of data up to this M15 candle
        m15w = m15_df[m15_df.index <= m15_time].tail(500).copy()
        m5_wind = m5_df[m5_df.index <= m15_time]
        m5w = m5_wind.tail(500).copy()
        
        if len(m15w) < 50 or len(m5w) < 50:
            continue
        
        # Compute indicators
        try:
            m5_ind = compute_all_indicators(m5w)
            m15_ind = compute_all_indicators(m15w)
        except Exception as e:
            continue
        
        if m5_ind is None or m15_ind is None:
            continue
        if m5_ind.get("atr") is None or len(m5_ind["atr"]) == 0:
            continue
        
        atr_val = float(m5_ind["atr"].iloc[-1])
        if atr_val < MIN_ATR:
            continue
        
        current_price = float(m15w["close"].iloc[-1])
        
        # ============================================================
        # REPLICATE EXACT FILTERS FROM v22_cycle()
        # ============================================================
        
        # 1. Trading hours check
        if not (TRADE_HOURS_START <= hour < TRADE_HOURS_END):
            continue
        
        # 2. Friday block after 18:00 UTC
        if weekday == 4 and hour >= 18:
            continue
        
        # 3. ADX
        try:
            adx_series = compute_adx(m5w["high"], m5w["low"], m5w["close"], period=14)
            adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0
        except Exception:
            adx_val = 0
        
        # 4. Spread estimation
        spread = estimate_spread(m5w)
        spread_ok = spread <= MAX_SPREAD_POINTS
        
        # 5. Run strategy
        try:
            empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
            empty_m1_ohlcv = m5w.tail(20)
            result = strategy.analyze(
                m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
                m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None,
            )
        except Exception:
            continue
        
        direction = result.get("direction", "NONE")
        score = result.get("setup_score", 0)
        
        # 6. Score filter
        if direction == "NONE" or score < MIN_SCORE:
            continue
        
        # 7. RSI confluence filter
        try:
            rsi_bullish = m5_ind["rsi"].iloc[-1] > 40 and m15_ind["rsi"].iloc[-1] > 40
            rsi_bearish = m5_ind["rsi"].iloc[-1] < 60 and m15_ind["rsi"].iloc[-1] < 60
            if direction == "BUY" and not rsi_bullish:
                trading_session_stats["rejected_rsi"] += 1
                continue
            if direction == "SELL" and not rsi_bearish:
                trading_session_stats["rejected_rsi"] += 1
                continue
        except Exception:
            pass
        
        # 8. EMA200 filter
        closes = m15w["close"].values
        if len(closes) >= 200:
            ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
            if len(ema200) >= 10:
                rising = float(ema200[-1]) > float(ema200[-10])
                if direction == "BUY" and not rising:
                    trading_session_stats["rejected_ema"] += 1
                    continue
                if direction == "SELL" and rising:
                    trading_session_stats["rejected_ema"] += 1
                    continue
        
        # 9. Volatility filter
        try:
            vo = vf.analyze(
                m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5w, m15_ohlcv=m15w,
                m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
            )
            if not vo.get("trade_ok", False):
                trading_session_stats["rejected_vol"] += 1
                continue
        except Exception:
            pass
        
        # 10. Spread filter
        if not spread_ok:
            trading_session_stats["rejected_spread"] += 1
            continue
        
        # ============================================================
        # TRADE SIGNAL PASSED ALL FILTERS!
        # ============================================================
        
        # Calculate trade details
        trade = simulate_missed_trade(direction, current_price, atr_val, adx_val, m15_time)
        trade["timestamp"] = m15_time
        trade["score"] = score
        trade["reason"] = result.get("reason", "")
        trade["session"] = result.get("session", "")
        trade["bias"] = result.get("bias", "")
        trade["source"] = "mean_reversion" if result.get("is_mean_reversion") else "trend_continuation"
        trade["spread"] = spread
        trade["m5_rsi"] = round(float(m5_ind["rsi"].iloc[-1]), 1) if "rsi" in m5_ind else None
        trade["m15_rsi"] = round(float(m15_ind["rsi"].iloc[-1]), 1) if "rsi" in m15_ind else None
        
        backtest_signals.append(trade)
        
        # Print
        print(f"{m15_time.strftime('%Y-%m-%d %H:%M'):<22} {current_price:<12.2f} {direction:<8} {score:<8} {atr_val:<8.2f} {adx_val:<8.1f} "
              f"{direction} SL={trade['sl']} TP={trade['tp']} lot={trade['lot']} | {trade['source']} (spread={spread})")
        
        trading_session_stats["signals"] += 1
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 BACKTEST SUMMARY")
    print("=" * 70)
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    print(f"Backtest period: {cutoff.strftime('%Y-%m-%d %H:%M UTC')} -> {now_str}")
    print(f"Trading hours: {TRADE_HOURS_START}:00-{TRADE_HOURS_END}:00 UTC")
    print(f"Total signals generated: {len(backtest_signals)}")
    
    if backtest_signals:
        buys = [s for s in backtest_signals if s["direction"] == "BUY"]
        sells = [s for s in backtest_signals if s["direction"] == "SELL"]
        print(f"BUY signals: {len(buys)} | SELL signals: {len(sells)}")
        
        total_risk = sum(s["estimated_risk"] for s in backtest_signals)
        print(f"Total risk exposure: ${total_risk:.2f} ({len(backtest_signals)} trades × ~$5.78 each)")
        print()
        
        print("DETAILED TRADE LIST:")
        print("-" * 110)
        print(f"{'#':<4} {'Time':<18} {'Dir':<6} {'Price':<10} {'SL':<10} {'TP':<10} {'Lot':<8} {'Score':<6} {'ATR':<8} {'ADX':<6} {'Session':<12} {'Type':<18}")
        print("-" * 110)
        for i, t in enumerate(backtest_signals, 1):
            ts = t["timestamp"].strftime('%m/%d %H:%M') if hasattr(t["timestamp"], 'strftime') else str(t["timestamp"])
            print(f"{i:<4} {ts:<18} {t['direction']:<6} {t['entry_price']:<10.2f} {t['sl']:<10.2f} {t['tp']:<10.2f} "
                  f"{t['lot']:<8.4f} {t['score']:<6} {t['atr']:<8.2f} {t['adx']:<6.1f} {t['session']:<12} {t['source']:<18}")
    else:
        print("❌ NO SIGNALS GENERATED - Bot would have been idle")
    
    print()
    print("REJECTION STATS:")
    for k, v in trading_session_stats.items():
        print(f"  {k}: {v}")
    
    return backtest_signals


def save_results(signals):
    """Save results to JSON file."""
    if not signals:
        print("\n⚠️  No signals to save.")
        return
    
    # Convert timestamps
    sigs_json = []
    for s in signals:
        s_copy = dict(s)
        if hasattr(s_copy.get("timestamp"), 'isoformat'):
            s_copy["timestamp"] = s_copy["timestamp"].isoformat()
        sigs_json.append(s_copy)
    
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_signals": len(signals),
        "signals": sigs_json,
    }
    
    output_path = os.path.join(os.path.dirname(__file__), "..", "logs", "backtest_24h_results.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n✅ Results saved to: {output_path}")


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 V22 Gold Scalping Bot - 24h Backtest")
    print("=" * 70)
    
    import argparse
    parser = argparse.ArgumentParser(description="Backtest bot for missed trades")
    parser.add_argument("--hours", type=int, default=48, help="Hours to look back (default: 48)")
    args = parser.parse_args()
    
    # Run backtest
    signals = run_backtest(hours_back=args.hours)
    
    # Save
    save_results(signals)
    
    print("\n" + "=" * 70)
    print("✅ BACKTEST COMPLETE")
    print("=" * 70)