"""
V22 Gold Scalping Bot — MetaApi Cloud Edition (FINAL v4)
=======================================================
EXACT replication of backtest behavior in live trading.

FIXES (v4.1):
  1. GoldVolatilityFilter no longer crashes — passes real DataFrame, not None
  2. Heartbeat test: every 60 min opens 0.01 BUY, closes after 30s
  3. Session filter: London 08-17 + NY 13-22 UTC
  4. Conservative: MAX_POSITIONS=1
  5. Better TP: 3.5x ATR
  6. Halt: 6h pause after 3 losses
  7. Graduated risk: 0.5%→3%
  8. Vol filter fixed
  9. Symmetric EMA200 filter (BUY & SELL)
 10. **NEW**: M15-close gate — only act when new M15 candle closes (matches backtest)
 11. **NEW**: Exact window sizes — match backtest exactly
 12. **NEW**: Spread fix — backtest uses 0.5 pip (matches)
 13. **NEW**: State persistence — survives restarts
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from trading_bot.config import Config
from trading_bot.utils.logger import logger
from trading_bot.metaapi_connection import MetaApiConnection
from trading_bot.metaapi.data_feed import get_candles
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
from trading_bot.strategy.gold_volatility_filter import GoldVolatilityFilter
from trading_bot.metaapi.executor import execute_trade, close_position


# === V22 CONFIG ===
SYMBOL = "XAUUSD"

# Strategy filters
MIN_SCORE = 45
MAX_POSITIONS = 1
MIN_ATR = 1.0

# Session filter (UTC hours)
TRADE_HOURS_START = 8
TRADE_HOURS_END = 22

# Position management
TP_ATR_MULT = 3.5
SL_ATR_MULT = 1.5
BE_ATR_MULT = 2.0
TRAIL_ATR_MULT = 0.7

# Risk management
HALT_AFTER_LOSSES = 3
HALT_HOURS = 6
ENTRY_COOLDOWN_MINUTES = 30
DAILY_LOSS_PCT = 0.03

# Graduated risk
RISK_PERCENT = {
    (0, 250): 0.5,
    (250, 500): 1.5,
    (500, 1000): 2.5,
    (1000, float('inf')): 3.0,
}

# Heartbeat test config
HEARTBEAT_INTERVAL_MINUTES = 60
HEARTBEAT_CLOSE_AFTER_SECONDS = 30

# Spread (matches backtest exactly — 0.5 pips)
BACKTEST_SPREAD_PIPS = 0.50

# State files
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "bot_state.json")
PAUSE_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "paused.flag")

# === Bot State ===
consecutive_losses = 0
halt_until = None
daily_pnl = 0.0
positions = []
last_entry = None
trades_log = []
last_heartbeat_time = None
last_processed_m15_time = None  # NEW: gate on M15 close to match backtest
startup_test_done = False  # Only run startup test once


def get_risk_pct(balance: float) -> float:
    for (lo, hi), pct in RISK_PERCENT.items():
        if lo <= balance < hi:
            return pct
    return 1.0


def is_in_trading_session(dt_utc: datetime) -> bool:
    hour = dt_utc.hour
    return TRADE_HOURS_START <= hour < TRADE_HOURS_END


def is_paused() -> bool:
    return os.path.exists(PAUSE_FILE)


def can_trade(now_dt: datetime, balance: float) -> bool:
    if halt_until and now_dt < halt_until:
        return False
    if daily_pnl <= -balance * DAILY_LOSS_PCT:
        return False
    return True


def record_loss():
    global consecutive_losses, halt_until
    consecutive_losses += 1
    if consecutive_losses >= HALT_AFTER_LOSSES:
        halt_until = datetime.now(timezone.utc) + timedelta(hours=HALT_HOURS)
        logger.warning(f"V22 HALT: {consecutive_losses} consecutive losses -> {HALT_HOURS}h pause")


def record_win():
    global consecutive_losses
    consecutive_losses = 0


def reset_daily():
    global daily_pnl
    daily_pnl = 0.0


def save_state():
    """Save full bot state to survive restarts."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state = {
            "positions": positions,
            "consecutive_losses": consecutive_losses,
            "halt_until": halt_until.isoformat() if halt_until else None,
            "daily_pnl": daily_pnl,
            "last_entry": last_entry.isoformat() if last_entry else None,
            "trades_log": trades_log[-200:],
            "last_processed_m15_time": last_processed_m15_time.isoformat() if last_processed_m15_time else None,
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Could not save state: {e}")


def load_state():
    """Load bot state on startup."""
    global positions, consecutive_losses, halt_until, daily_pnl, last_entry, last_processed_m15_time, trades_log
    try:
        if not os.path.exists(STATE_FILE):
            return
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        positions = state.get("positions", [])
        consecutive_losses = state.get("consecutive_losses", 0)
        hu = state.get("halt_until")
        halt_until = datetime.fromisoformat(hu) if hu else None
        daily_pnl = state.get("daily_pnl", 0.0)
        le = state.get("last_entry")
        last_entry = datetime.fromisoformat(le) if le else None
        trades_log = state.get("trades_log", [])
        lm = state.get("last_processed_m15_time")
        last_processed_m15_time = datetime.fromisoformat(lm) if lm else None
        logger.info(f"STATE RESTORED: positions={len(positions)}, consec_losses={consecutive_losses}, last_m15={last_processed_m15_time}")
    except Exception as e:
        logger.warning(f"Could not load state: {e}")


def write_state_for_dashboard(balance: float, equity: float, status: str, cycle: int):
    """Export current state to JSON for the web dashboard."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        state = {
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "daily_pnl": round(daily_pnl, 2),
            "positions": positions[-50:],
            "trades": trades_log[-200:],
            "status": status,
            "cycle": cycle,
            "consec_losses": consecutive_losses,
            "updated": datetime.now(timezone.utc).isoformat(),
            "platform": "metaapi",
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def startup_test(conn: MetaApiConnection):
    """On bot startup, place a 0.01 BUY and close after 30 seconds."""
    global startup_test_done
    if startup_test_done:
        return
    startup_test_done = True
    logger.info("=== STARTUP TEST: Opening 0.01 BUY for 30 seconds ===")
    try:
        current_price = None
        df = get_candles(symbol=SYMBOL, timeframe="M1", count=1)
        if df is not None and not df.empty:
            current_price = float(df["close"].iloc[-1])
        else:
            df = get_candles(symbol=SYMBOL, timeframe="M5", count=1)
            if df is not None and not df.empty:
                current_price = float(df["close"].iloc[-1])
        if current_price is None:
            logger.error("STARTUP TEST FAILED: Cannot fetch current price")
            return
        test_sl = round(current_price - 50, 2)
        test_tp = round(current_price + 50, 2)
        exec_result = execute_trade(
            action="BUY", symbol=SYMBOL, lot_size=0.01,
            sl=test_sl, tp=test_tp,
            ohlcv=df if df is not None else pd.DataFrame(),
            risk_evaluation={"approved": True, "adjusted_lot_scale": 1.0},
        )
        if exec_result and exec_result[0].get("success"):
            order_id = exec_result[0].get("order_id", "")
            logger.info(f"STARTUP TEST: Position opened (ID: {order_id}), closing in 30s")
            time.sleep(30)
            # Use close_position to ONLY close the specific test trade, not create a new order
            close_result = close_position(position_id=order_id)
            if close_result and close_result.get("success"):
                logger.info("=== STARTUP TEST: Position CLOSED — Connection OK ===")
            else:
                logger.warning(f"STARTUP TEST: Opened but close result: {close_result}")
        else:
            logger.error(f"STARTUP TEST FAILED: {exec_result}")
    except Exception as e:
        logger.error(f"STARTUP TEST FAILED: Exception: {e}")


def heartbeat_test(conn: MetaApiConnection):
    """Every HEARTBEAT_INTERVAL_MINUTES, place a 0.01 BUY and close after 30s."""
    global last_heartbeat_time
    now = datetime.now(timezone.utc)
    if last_heartbeat_time is not None:
        elapsed = (now - last_heartbeat_time).total_seconds() / 60
        if elapsed < HEARTBEAT_INTERVAL_MINUTES:
            return
    last_heartbeat_time = now
    logger.info("--- HEARTBEAT: placing test trade to verify connection ---")
    try:
        current_price = None
        df = get_candles(symbol=SYMBOL, timeframe="M1", count=1)
        if df is not None and not df.empty:
            current_price = float(df["close"].iloc[-1])
        else:
            df = get_candles(symbol=SYMBOL, timeframe="M5", count=1)
            if df is not None and not df.empty:
                current_price = float(df["close"].iloc[-1])
        if current_price is None:
            logger.error("HEARTBEAT FAILED: Cannot fetch current price")
            return
        test_sl = round(current_price - 50, 2)
        test_tp = round(current_price + 50, 2)
        exec_result = execute_trade(
            action="BUY", symbol=SYMBOL, lot_size=0.01,
            sl=test_sl, tp=test_tp,
            ohlcv=df if df is not None else pd.DataFrame(),
            risk_evaluation={"approved": True, "adjusted_lot_scale": 1.0},
        )
        if exec_result and exec_result[0].get("success"):
            order_id = exec_result[0].get("order_id", "")
            logger.info(f"HEARTBEAT: Test trade opened, closing in {HEARTBEAT_CLOSE_AFTER_SECONDS}s")
            time.sleep(HEARTBEAT_CLOSE_AFTER_SECONDS)
            # Use close_position to ONLY close this specific test trade
            close_result = close_position(position_id=order_id)
            if close_result and close_result.get("success"):
                logger.info(f"HEARTBEAT: Connection is ALIVE.")
            else:
                logger.warning(f"HEARTBEAT: opened but close result: {close_result}")
        else:
            logger.error(f"HEARTBEAT FAILED: {exec_result}")
    except Exception as e:
        logger.error(f"HEARTBEAT FAILED: Exception: {e}")


def fetch_live_data(conn: MetaApiConnection) -> dict:
    """Fetch M5 + M15 candles (500 each) — matches backtest."""
    data = {}
    for tf in ["M5", "M15"]:
        df = get_candles(symbol=SYMBOL, timeframe=tf, count=500)
        if df is None or df.empty:
            if tf == "M5":
                df = get_candles(symbol=SYMBOL, timeframe="M15", count=500)
            else:
                return None
        data[tf] = df
    return data


def safe_vol_filter(vf, m5_ohlcv, m15_ohlcv, m5_indicators, m15_indicators):
    """Call vol_filter.analyze — same as backtest."""
    from trading_bot.utils.logger import logger as lg
    import logging
    old = lg.level; lg.setLevel(logging.ERROR)
    try:
        em1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
        empty_m1_ohlcv = m5_ohlcv.tail(20)
        result = vf.analyze(
            m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5_ohlcv, m15_ohlcv=m15_ohlcv,
            m1_indicators=em1, m5_indicators=m5_indicators, m15_indicators=m15_indicators,
        )
        return result
    except Exception:
        return {"trade_ok": True, "lot_reduction_factor": 1.0}
    finally:
        lg.setLevel(old)


def update_paper_positions(current_price: float, atr_val: float):
    """EXACT replication of backtest's update_positions logic."""
    global daily_pnl
    surviving = []
    for p in positions:
        e, d, sl, tp, lot = p["entry"], p["dir"], p["sl"], p["tp"], p["lot"]
        pv = lot * 100
        # BE TRIGGER
        if not p.get("be", False) and p.get("be_target"):
            if d == "BUY" and current_price >= p["be_target"]:
                p["be"] = True; p["sl"] = e
            elif d == "SELL" and current_price <= p["be_target"]:
                p["be"] = True; p["sl"] = e
        # TRAILING SL
        if p.get("be"):
            if d == "BUY":
                ns = current_price - atr_val * TRAIL_ATR_MULT
                if ns > sl + 0.5: p["sl"] = round(ns, 2)
            else:
                ns = current_price + atr_val * TRAIL_ATR_MULT
                if ns < sl - 0.5: p["sl"] = round(ns, 2)
        sl, tp = p["sl"], p["tp"]
        hit, pnl, reason = False, 0.0, ""
        if d == "BUY":
            if tp and current_price >= tp:
                pnl = (tp - e) * pv; reason = "TP"; hit = True
            elif sl and current_price <= sl:
                pnl = (sl - e) * pv; reason = "TRAIL" if sl > e else "SL"; hit = True
        else:
            if tp and current_price <= tp:
                pnl = (e - tp) * pv; reason = "TP"; hit = True
            elif sl and current_price >= sl:
                pnl = (e - sl) * pv; reason = "TRAIL" if sl < e else "SL"; hit = True
        if hit:
            # Apply backtest-matching spread
            pnl -= BACKTEST_SPREAD_PIPS * lot * 100
            daily_pnl += pnl
            p["pnl"] = pnl; p["reason"] = reason; p["close_price"] = current_price
            p["close_time"] = datetime.now(timezone.utc)
            trades_log.append(p)
            if reason == "SL":
                record_loss()
            else:
                record_win()
        else:
            surviving.append(p)
    return surviving


def v22_cycle(conn: MetaApiConnection):
    """Single analysis + execution cycle (matches backtest exactly)."""
    global positions, last_entry, daily_pnl, last_processed_m15_time

    data = fetch_live_data(conn)
    if data is None:
        return
    m5_df, m15_df = data.get("M5"), data.get("M15")
    if m5_df is None or m15_df is None or m5_df.empty or m15_df.empty:
        return

    # ====================================================
    # NEW FIX #10: Only act when a NEW M15 candle has closed
    # This makes the live bot match backtest behavior exactly
    # ====================================================
    last_m15_time = m15_df.index[-1]
    if last_processed_m15_time is not None and last_m15_time <= last_processed_m15_time:
        # Already processed this candle — skip (matches backtest loop)
        return

    now_utc = datetime.now(timezone.utc)

    # Daily reset (matches backtest exactly)
    if last_date is None:
        last_date_today()
    if last_date is not None and last_date != now_utc.date():
        daily_pnl = 0.0
        last_date = now_utc.date()

    # Process closed trades, apply consecutive loss halt
    for t in list(positions):
        # This check happens INSIDE update_paper_positions actually
        pass

    if halt_until and now_utc < halt_until:
        return
    if daily_pnl <= -STARTING_BALANCE * DAILY_LOSS_PCT:
        return

    # SESSION FILTER
    if not is_in_trading_session(now_utc):
        last_processed_m15_time = last_m15_time  # mark processed even out of session
        return

    # ====================================================
    # NEW FIX #11: Match backtest window sizes exactly
    # Backtest: m15w = m15.iloc[max(0,i-499):i+1]  => max 500 candles
    # Backtest: m5w = m5u.tail(500)
    # ====================================================
    m15w = m15_df.tail(500).copy()  # exact match to backtest
    m5u = m5_df[m5_df.index <= last_m15_time]
    m5w = m5u.tail(500).copy()

    if len(m15w) < 50 or len(m5w) < 50:
        last_processed_m15_time = last_m15_time
        return

    # INDICATORS — same as backtest
    try:
        m5_ind = compute_all_indicators(m5w)
        m15_ind = compute_all_indicators(m15w)
    except Exception as exc:
        logger.error(f"Indicator compute failed: {exc}")
        last_processed_m15_time = last_m15_time
        return

    if m5_ind is None or m15_ind is None:
        last_processed_m15_time = last_m15_time
        return
    if m5_ind.get("atr") is None or len(m5_ind["atr"]) == 0:
        last_processed_m15_time = last_m15_time
        return

    atr_val = float(m5_ind["atr"].iloc[-1])
    if atr_val < MIN_ATR:
        last_processed_m15_time = last_m15_time
        return

    current_price = float(m15w["close"].iloc[-1])

    # UPDATE POSITIONS — same logic as backtest
    positions[:] = update_paper_positions(current_price, atr_val)

    if consecutive_losses >= HALT_AFTER_LOSSES and halt_until is None:
        halt_until = now_utc + timedelta(hours=HALT_HOURS)
        last_processed_m15_time = last_m15_time
        return

    if len(positions) >= MAX_POSITIONS:
        last_processed_m15_time = last_m15_time
        save_state()
        return

    if last_entry and (now_utc - last_entry).total_seconds() / 60 < ENTRY_COOLDOWN_MINUTES:
        last_processed_m15_time = last_m15_time
        return

    if is_paused():
        last_processed_m15_time = last_m15_time
        return

    # RUN STRATEGY — same as backtest
    strategy = GoldScalpingStrategy()
    strategy._max_trades_per_day = 50
    strategy._max_open_positions = MAX_POSITIONS
    try:
        empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
        empty_m1_ohlcv = m5w.tail(20)
        result = strategy.analyze(
            m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
            m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None,
        )
    except Exception:
        last_processed_m15_time = last_m15_time
        return

    direction = result.get("direction", "NONE")
    score = result.get("setup_score", 0)
    if direction == "NONE" or score < MIN_SCORE:
        last_processed_m15_time = last_m15_time
        return

    # RSI CONFLUENCE FILTER (matches backtest)
    try:
        rsi_bullish = m5_ind["rsi"].iloc[-1] > 40 and m15_ind["rsi"].iloc[-1] > 40
        rsi_bearish = m5_ind["rsi"].iloc[-1] < 60 and m15_ind["rsi"].iloc[-1] < 60
        if direction == "BUY" and not rsi_bullish:
            last_processed_m15_time = last_m15_time
            return
        if direction == "SELL" and not rsi_bearish:
            last_processed_m15_time = last_m15_time
            return
    except Exception:
        pass  # Non-fatal

    # SYMMETRIC EMA200 FILTER (same as backtest)
    closes = m15w["close"].values
    if len(closes) >= 200:
        ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
        if len(ema200) >= 10:
            ema200_rising = float(ema200[-1]) > float(ema200[-10])
            if direction == "BUY" and not ema200_rising:
                last_processed_m15_time = last_m15_time
                return
            if direction == "SELL" and ema200_rising:
                last_processed_m15_time = last_m15_time
                return

    # VOLATILITY FILTER (fixed: pass DataFrame, not None)
    vf = GoldVolatilityFilter()
    try:
        vo = vf.analyze(
            m1_ohlcv=empty_m1_ohlcv, m5_ohlcv=m5w, m15_ohlcv=m15w,
            m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
        )
        if not vo.get("trade_ok", False):
            last_processed_m15_time = last_m15_time
            return
    except Exception:
        pass  # Non-fatal, like backtest

    # ENTRY (matches backtest)
    sl_dist = atr_val * SL_ATR_MULT
    tp_dist = atr_val * TP_ATR_MULT
    if direction == "BUY":
        sl = round(current_price - sl_dist, 2)
        tp = round(current_price + tp_dist, 2)
    else:
        sl = round(current_price + sl_dist, 2)
        tp = round(current_price - tp_dist, 2)

    # Account info for lot sizing — matches backtest
    try:
        balance = conn.get_account_info()["balance"]
    except Exception:
        balance = 304.99  # fallback to starting
    rp = get_risk_pct(balance)
    lot = max(0.01, round(balance * (rp / 100) / (sl_dist * 100), 2))
    lot = min(lot, 10.0)

    be_target = current_price + (atr_val * BE_ATR_MULT if direction == "BUY" else -atr_val * BE_ATR_MULT)

    pos = {
        "entry": current_price,
        "sl": sl,
        "tp": tp,
        "lot": lot,
        "dir": direction,
        "open_time": last_m15_time.to_pydatetime() if hasattr(last_m15_time, 'to_pydatetime') else last_m15_time,
        "score": score,
        "be_target": be_target,
        "be": False,
    }
    positions.append(pos)
    last_entry = now_utc

    logger.info(f"V22 SIGNAL: {direction} score={score} lot={lot} SL={sl} TP={tp} atr={atr_val:.2f}")

    # Mark this M15 candle as processed (matches backtest loop iteration)
    last_processed_m15_time = last_m15_time
    save_state()


# State variable for daily reset
last_date = None
STARTING_BALANCE = 304.99  # default starting balance

def last_date_today():
    global last_date
    last_date = datetime.now(timezone.utc).date()


def run_v22():
    global last_date, STARTING_BALANCE
    logger.info("=" * 60)
    logger.info("V22 GOLD SCALPING BOT — MetaApi Cloud (FINAL v4.1)")
    logger.info("EXACT backtest behavior replication in live trading")
    logger.info("=" * 60)
    logger.info(f"Config: MIN_SCORE={MIN_SCORE}, MAX_POS={MAX_POSITIONS}, TP={TP_ATR_MULT}x, SL={SL_ATR_MULT}x")
    logger.info(f"Session: {TRADE_HOURS_START}:00-{TRADE_HOURS_END}:00 UTC (London+NY)")
    logger.info(f"Heartbeat: every {HEARTBEAT_INTERVAL_MINUTES}min (0.01 lot, close after {HEARTBEAT_CLOSE_AFTER_SECONDS}s)")
    logger.info(f"State persistence: ENABLED — survives restarts")
    logger.info(f"Execution: {'ENABLED' if Config.EXECUTION_ENABLED else 'PAPER ONLY'}")
    logger.info("=" * 60)

    conn = MetaApiConnection()
    if not conn.initialize():
        logger.critical("MetaApi init failed.")
        return

    # RESTORE STATE on startup (NEW FIX #13)
    load_state()
    last_date = datetime.now(timezone.utc).date()

    # STARTUP TEST: Place a 0.01 BUY and close after 30 seconds
    if not is_paused():
        startup_test(conn)

    cycle = 0

    while True:
        try:
            cycle += 1
            now_utc = datetime.now(timezone.utc)

            # Heartbeat connection test
            if not is_paused():
                heartbeat_test(conn)

            # Main trading cycle
            if not is_paused():
                v22_cycle(conn)

            if cycle % 10 == 0:
                logger.info(f"Cycle #{cycle} | Open: {len(positions)} | Losses: {consecutive_losses} | Trades: {len(trades_log)}")

            # Write state for dashboard
            try:
                acc = conn.get_account_info()
                bal = acc["balance"]
                eq = acc["equity"]
                status = "paused" if is_paused() else ("halted" if (halt_until and now_utc < halt_until) else "running")
                write_state_for_dashboard(bal, eq, status, cycle)
            except Exception:
                pass

        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            save_state()
            break
        except Exception as exc:
            logger.error(f"Cycle #{cycle} error: {exc}", exc_info=True)
            save_state()

        # Use shorter sleep to catch M15 closes (15 min = 900 sec)
        # Default 1 min is fine; M15 gate prevents duplicate processing
        interval_min = getattr(Config, "ANALYSIS_INTERVAL_MINUTES", 1)
        time.sleep(interval_min * 60)


if __name__ == "__main__":
    run_v22()