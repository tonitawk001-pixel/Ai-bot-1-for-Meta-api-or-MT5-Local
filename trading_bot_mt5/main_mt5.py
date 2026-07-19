"""
V22 Gold Scalping Bot — Local MT5 Edition
==========================================
Runs directly on your laptop via MetaTrader5 Python library.
No MetaApi, no cloud — direct connection to your broker via MT5 terminal.

SAME strategy as the Contabo/MetaApi version:
  - EMA200 trend filter
  - RSI confluence (M5 >40, M15 >40 for BUY; M5 <60, M15 <60 for SELL)
  - ADX dynamic TP (5x ATR when ADX > 25)
  - 2% flat risk per trade
  - Breakeven at 2x ATR
  - Friday 18:00 UTC entry block / 21:00 UTC auto-close
  - 3-loss halt / daily loss limit
"""

import os
import sys
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
import atexit
from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np

# Local MT5 connection
from mt5_connection import MT5Connection

# Standalone logger (no project dependency needed)
from logger_mt5 import logger

# Telegram notifier
import telegram_notifier as tg

# Shared modules from main project
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy

# ===== CONFIG =====
SYMBOL = "XAUUSD"
MIN_SCORE = 45
MAX_POSITIONS = 1
MIN_ATR = 1.0
TRADE_HOURS_START = 8
TRADE_HOURS_END = 22

TP_ATR_MULT = 3.5
TP_ATR_MULT_TREND = 5.0
SL_ATR_MULT = 1.5
BE_ATR_MULT = 2.0
TRAIL_ATR_MULT = 0.7
BE_BUFFER_POINTS = 12

RISK_PERCENT_FLAT = 2.0

HALT_AFTER_LOSSES = 3
HALT_HOURS = 6
ENTRY_COOLDOWN_MINUTES = 30
DAILY_LOSS_PCT = 0.03
ADX_TREND_THRESHOLD = 25

MAX_SPREAD_POINTS = 30
STATE_FILE = "bot_state.json"

# Global state
consecutive_losses = 0
halt_until = None
daily_pnl = 0.0
last_entry = None
last_processed_m15_time = None
last_date = None
STARTING_BALANCE = 304.99

positions = []
trades_log = []
be_modified_ids = set()


def get_risk_pct(b):
    return RISK_PERCENT_FLAT / 100.0


def is_in_trading_session(dt):
    return TRADE_HOURS_START <= dt.hour < TRADE_HOURS_END


def is_friday_entry_blocked(dt):
    return dt.weekday() == 4 and dt.hour >= 18


def is_friday_close(dt):
    return dt.weekday() == 4 and dt.hour >= 21


def save_state():
    try:
        state = {
            "positions": positions,
            "consecutive_losses": consecutive_losses,
            "halt_until": halt_until.isoformat() if halt_until else None,
            "daily_pnl": daily_pnl,
            "last_entry": last_entry.isoformat() if last_entry else None,
            "trades_log": trades_log[-200:],
            "last_processed_m15_time": last_processed_m15_time.isoformat() if last_processed_m15_time else None,
            "be_modified_ids": list(be_modified_ids),
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2, default=str)
        logger.info("State saved.")
    except Exception as e:
        logger.error(f"Save state failed: {e}")


def load_state():
    global positions, consecutive_losses, halt_until, daily_pnl, last_entry, trades_log, last_processed_m15_time, be_modified_ids
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE) as f:
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
        be_modified_ids = set(state.get("be_modified_ids", []))
        logger.info(f"State restored: {len(positions)} positions, {len(trades_log)} trades")
    except Exception as e:
        logger.warning(f"Load state failed: {e}")


def calculate_lot_size(balance, sl_distance):
    if sl_distance <= 0 or balance <= 0:
        return 0.01
    risk_amount = balance * 0.02
    risk_per_lot = sl_distance * 100
    raw_lot = risk_amount / risk_per_lot
    raw_lot = round(raw_lot / 0.01) * 0.01
    return max(0.01, min(raw_lot, 10.0))


def compute_adx(high, low, close, period=14):
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


def fetch_live_data(mt5):
    """Fetch M5 and M15 candles from local MT5."""
    data = {}
    for tf in ["M5", "M15"]:
        df = mt5.get_candles(SYMBOL, tf, 500)
        if df is None or df.empty:
            if tf == "M5":
                df = mt5.get_candles(SYMBOL, "M15", 500)
            else:
                return None
        data[tf] = df
    return data


def update_positions(current_price, atr_val, mt5):
    """Update trailing SL, breakeven, and close hit positions."""
    global daily_pnl, consecutive_losses
    surviving = []
    for p in positions:
        entry, direction, sl, tp, lot = p["entry"], p["dir"], p["sl"], p["tp"], p["lot"]
        pv = lot * 100
        pos_id = p.get("position_id", "")

        # Live breakeven
        if pos_id and pos_id not in be_modified_ids:
            be_price = entry + (atr_val * BE_ATR_MULT) if direction == "BUY" else entry - (atr_val * BE_ATR_MULT)
            be_hit = (direction == "BUY" and current_price >= be_price) or (direction == "SELL" and current_price <= be_price)
            if be_hit:
                buffer = BE_BUFFER_POINTS * 0.01
                new_sl = round(entry + buffer if direction == "BUY" else entry - buffer, 2)
                try:
                    result = mt5.modify_position(pos_id, new_sl, tp)
                    if result and result.get("success"):
                        p["sl"] = new_sl
                        p["be"] = True
                        be_modified_ids.add(pos_id)
                        logger.info(f"[BREAKEVEN] Position {pos_id} secured at {new_sl}")
                except Exception as e:
                    logger.warning(f"[BREAKEVEN] Failed: {e}")

        # In-memory trailing
        if not p.get("be", False) and p.get("be_target"):
            if direction == "BUY" and current_price >= p["be_target"]:
                p["be"] = True; p["sl"] = entry
            elif direction == "SELL" and current_price <= p["be_target"]:
                p["be"] = True; p["sl"] = entry
        if p.get("be"):
            ns = current_price - atr_val * TRAIL_ATR_MULT if direction == "BUY" else current_price + atr_val * TRAIL_ATR_MULT
            if direction == "BUY" and ns > sl + 0.5:
                p["sl"] = round(ns, 2)
                if pos_id:
                    mt5.modify_position(pos_id, round(ns, 2), tp)
            elif direction == "SELL" and ns < sl - 0.5:
                p["sl"] = round(ns, 2)
                if pos_id:
                    mt5.modify_position(pos_id, round(ns, 2), tp)

        sl, tp = p["sl"], p["tp"]
        hit, pnl, reason = False, 0.0, ""
        if direction == "BUY":
            if tp and current_price >= tp:
                pnl = (tp - entry) * pv; reason = "TP"; hit = True
            elif sl and current_price <= sl:
                pnl = (sl - entry) * pv; reason = "TRAIL" if sl > entry else "SL"; hit = True
        else:
            if tp and current_price <= tp:
                pnl = (entry - tp) * pv; reason = "TP"; hit = True
            elif sl and current_price >= sl:
                pnl = (entry - sl) * pv; reason = "TRAIL" if sl < entry else "SL"; hit = True
        if hit:
            pnl -= 0.50 * lot * 100
            daily_pnl += pnl
            p["pnl"] = pnl; p["reason"] = reason; p["close_price"] = current_price
            p["close_time"] = datetime.now(timezone.utc)
            trades_log.append(p)
            if pos_id and reason in ("TP", "SL", "TRAIL"):
                mt5.close_position(pos_id)
            if reason == "SL":
                consecutive_losses += 1
            else:
                consecutive_losses = 0
        else:
            surviving.append(p)
    return surviving


def main():
    global last_date, daily_pnl, last_entry, last_processed_m15_time, halt_until, consecutive_losses, positions, trades_log

    logger.info("=" * 60)
    logger.info("V22 GOLD SCALPING BOT — Local MT5 Edition")
    logger.info("Direct connection to your MT5 terminal")
    logger.info("=" * 60)

    # Initialize MT5 connection
    mt5 = MT5Connection()
    if not mt5.initialize():
        logger.critical("Failed to initialize MT5 connection. Make sure MT5 is running and logged in.")
        input("Press Enter to exit...")
        return

    atexit.register(mt5.shutdown)
    load_state()
    last_date = datetime.now(timezone.utc).date()
    
    # Telegram startup
    acc_info = mt5.get_account_info()
    acc_name = f"Acc_{acc_info.get('login', '?')}"
    acc_balance = acc_info.get('balance', 0) if acc_info else 0
    tg.set_account_name(acc_name)
    
    # If CHAT_ID is already hardcoded (not 0), send startup directly
    if tg.CHAT_ID:
        tg.notify_startup(balance=acc_balance)
        logger.info("Telegram: Connected! Startup notification sent.")
    else:
        if tg.try_auto_detect_chat_id():
            tg.notify_startup(balance=acc_balance)
            logger.info("Telegram: Auto-detected and connected!")
        else:
            logger.info("Telegram: Not configured. Message @Trading77777Bot first.")

    strategy = GoldScalpingStrategy()
    strategy._max_trades_per_day = 50
    strategy._max_open_positions = MAX_POSITIONS

    cycle = 0
    logger.info("Bot started. Press Ctrl+C to stop.")

    while True:
        try:
            cycle += 1
            now_utc = datetime.now(timezone.utc)

            # Daily reset
            if last_date is None:
                last_date = now_utc.date()
            if last_date != now_utc.date():
                daily_pnl = 0.0
                last_date = now_utc.date()

            # Friday auto-close at 21:00 UTC
            if is_friday_close(now_utc):
                for p in list(positions):
                    pos_id = p.get("position_id", "")
                    if pos_id:
                        mt5.close_position(pos_id)
                        logger.info(f"[FRIDAY] Closed position {pos_id}")
                positions.clear()

            # Check connection
            info = mt5.get_account_info()
            if not info:
                logger.warning("MT5 not connected, retrying...")
                time.sleep(10)
                continue

            balance = info["balance"]

            # Halt check
            if halt_until and now_utc < halt_until:
                time.sleep(60)
                continue

            # Daily loss limit
            if daily_pnl <= -balance * DAILY_LOSS_PCT:
                logger.warning(f"Daily loss limit reached ({daily_pnl:.2f}). Stopping for the day.")
                time.sleep(300)
                continue

            # Session filter
            if not is_in_trading_session(now_utc):
                time.sleep(60)
                continue

            # Friday entry block
            if is_friday_entry_blocked(now_utc):
                logger.info(f"[FRIDAY] No entries after 18:00 UTC")
                time.sleep(60)
                continue

            # Fetch data
            data = fetch_live_data(mt5)
            if data is None:
                time.sleep(10)
                continue

            m5_df, m15_df = data.get("M5"), data.get("M15")
            if m5_df is None or m15_df is None or m5_df.empty or m15_df.empty:
                time.sleep(10)
                continue

            last_m15_time = m15_df.index[-1]
            if last_processed_m15_time is not None and last_m15_time <= last_processed_m15_time:
                time.sleep(10)
                continue

            m15w = m15_df.tail(500).copy()
            m5u = m5_df[m5_df.index <= last_m15_time]
            m5w = m5u.tail(500).copy()

            if len(m15w) < 50 or len(m5w) < 50:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue

            current_price = float(m15w["close"].iloc[-1])

            # Update positions
            positions[:] = update_positions(current_price, 0, mt5)  # ATR updated below

            if consecutive_losses >= HALT_AFTER_LOSSES and halt_until is None:
                halt_until = now_utc + timedelta(hours=HALT_HOURS)
                logger.warning(f"[HALT] {consecutive_losses} consecutive losses")
                save_state()
                time.sleep(60)
                continue

            if len(positions) >= MAX_POSITIONS:
                save_state()
                time.sleep(10)
                continue

            if last_entry and (now_utc - last_entry).total_seconds() / 60 < ENTRY_COOLDOWN_MINUTES:
                time.sleep(10)
                continue

            # Compute indicators
            m5_ind = compute_all_indicators(m5w)
            m15_ind = compute_all_indicators(m15w)
            if m5_ind is None or m15_ind is None:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue
            if m5_ind.get("atr") is None or len(m5_ind["atr"]) == 0:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue

            atr_val = float(m5_ind["atr"].iloc[-1])
            if atr_val < MIN_ATR:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue

            # ADX for dynamic TP
            try:
                adx_series = compute_adx(m5w["high"], m5w["low"], m5w["close"])
                adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0
            except:
                adx_val = 0

            tp_mult = TP_ATR_MULT_TREND if adx_val >= ADX_TREND_THRESHOLD else TP_ATR_MULT

            # Run strategy
            try:
                empty_m1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
                eo = m5w.tail(20)
                result = strategy.analyze(
                    m1_indicators=empty_m1, m5_indicators=m5_ind, m15_indicators=m15_ind,
                    m1_ohlcv=eo, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None,
                )
            except:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue

            direction = result.get("direction", "NONE")
            score = result.get("setup_score", 0)
            if direction == "NONE" or score < MIN_SCORE:
                last_processed_m15_time = last_m15_time
                time.sleep(10)
                continue

            # RSI confluence
            try:
                rsi_bullish = m5_ind["rsi"].iloc[-1] > 40 and m15_ind["rsi"].iloc[-1] > 40
                rsi_bearish = m5_ind["rsi"].iloc[-1] < 60 and m15_ind["rsi"].iloc[-1] < 60
                if direction == "BUY" and not rsi_bullish:
                    last_processed_m15_time = last_m15_time; continue
                if direction == "SELL" and not rsi_bearish:
                    last_processed_m15_time = last_m15_time; continue
            except:
                pass

            # EMA200 filter
            closes = m15w["close"].values
            if len(closes) >= 200:
                ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
                if len(ema200) >= 10:
                    rising = ema200[-1] > ema200[-10]
                    if direction == "BUY" and not rising:
                        last_processed_m15_time = last_m15_time; continue
                    if direction == "SELL" and rising:
                        last_processed_m15_time = last_m15_time; continue

            # Calculate SL/TP
            sl_dist = atr_val * SL_ATR_MULT
            tp_dist = atr_val * tp_mult

            if direction == "BUY":
                sl = round(current_price - sl_dist, 2)
                tp = round(current_price + tp_dist, 2)
            else:
                sl = round(current_price + sl_dist, 2)
                tp = round(current_price - tp_dist, 2)

            lot = calculate_lot_size(balance, sl_dist)
            be_target = current_price + (atr_val * BE_ATR_MULT if direction == "BUY" else -atr_val * BE_ATR_MULT)

            # Execute trade on MT5
            logger.info(f"[TRADE] {direction} {lot} lots at {current_price:.2f} SL={sl} TP={tp} (ADX={adx_val:.1f})")
            result = mt5.place_order(direction, SYMBOL, lot, sl, tp)

            if result and result.get("success"):
                order_id = result.get("order_id", "")
                logger.info(f"✅ ORDER EXECUTED: {direction} {lot} lots, ID: {order_id}")
                
                # Telegram notify
                tg.notify_trade_opened(direction, SYMBOL, current_price, lot, sl, tp, score, balance)

                pos = {
                    "entry": current_price,
                    "sl": sl,
                    "tp": tp,
                    "lot": lot,
                    "dir": direction,
                    "open_time": datetime.now(timezone.utc),
                    "score": score,
                    "be_target": be_target,
                    "be": False,
                    "position_id": order_id,
                }
                positions.append(pos)
                last_entry = now_utc
            else:
                reason = result.get("reason", "Unknown") if result else "No result"
                logger.error(f"❌ ORDER REJECTED: {reason}")

            last_processed_m15_time = last_m15_time
            save_state()

            # Telegram heartbeat every 5 min
            tg.notify_heartbeat(balance, len(positions), len(trades_log))

            if cycle % 10 == 0:
                logger.info(f"Cycle #{cycle} | Balance: ${balance:.2f} | Open: {len(positions)} | Trades: {len(trades_log)}")

        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            tg.notify_shutdown()
            save_state()
            break
        except Exception as e:
            logger.error(f"Cycle #{cycle} error: {e}")
            tg.notify_error(f"Cycle error: {str(e)[:100]}")
            save_state()

        time.sleep(60)

    # Bot stopped
    tg.notify_shutdown()
    mt5.shutdown()


if __name__ == "__main__":
    main()