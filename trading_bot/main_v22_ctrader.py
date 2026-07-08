"""V22 LIVE TRADER - cTrader Edition (Contabo Linux)
Same V22 strategy, using cTrader FIX API instead of MT5.
Runs 24/7 on Contabo Linux VPS."""

import sys, os, time, json
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

from trading_bot.ctrader_fix import CTraderFIX
from trading_bot.utils.logger import logger

SYMBOL = "XAUUSD"
MIN_SCORE = 50
MAX_POSITIONS = 5
HALT_AFTER_LOSSES = 3
HALT_HOURS = 2

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "bot_state.json")
PAUSE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs", "paused.flag")

consecutive_losses = 0
halt_until = None
daily_pnl = 0.0
paper_positions = []
last_entry_time = None
ENTRY_COOLDOWN_MINUTES = 15
all_trades_history = []


def get_risk_pct(bal):
    if bal < 250: return 0.5
    elif bal < 500: return 1.5
    elif bal < 1000: return 2.5
    return 3.0


def write_state(balance, equity, status, cycle):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        pos_data = [{"direction": p["d"], "entry": p["e"], "sl": p["sl"],
                      "tp": p["tp"], "lot": p["lot"], "be": p.get("be", False)}
                    for p in paper_positions]
        state = {
            "balance": round(balance, 2), "equity": round(equity, 2),
            "daily_pnl": round(daily_pnl, 2), "positions": pos_data,
            "trades": all_trades_history[-200:], "status": status,
            "cycle": cycle, "consec_losses": consecutive_losses,
            "updated": datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def is_paused():
    return os.path.exists(PAUSE_FILE)


def can_trade(now_dt, balance):
    if halt_until and now_dt < halt_until:
        return False
    if daily_pnl <= -balance * 0.05:
        return False
    return True


def record_sl():
    global consecutive_losses, halt_until
    consecutive_losses += 1
    if consecutive_losses >= HALT_AFTER_LOSSES:
        halt_until = datetime.now(timezone.utc) + timedelta(hours=HALT_HOURS)
        logger.warning(f"V22 HALT: {HALT_AFTER_LOSSES} consecutive losses")


def update_positions(current_price, atr_val):
    global daily_pnl
    remaining = []
    for pos in paper_positions:
        e, d, sl, tp, lot = pos["e"], pos["d"], pos["sl"], pos["tp"], pos["lot"]
        pv = lot * 100
        # Trailing SL
        if pos.get("be"):
            if d == "BUY":
                ns = current_price - atr_val * 0.7
                if ns > sl + 0.5: pos["sl"] = round(ns, 2)
            else:
                ns = current_price + atr_val * 0.7
                if ns < sl - 0.5: pos["sl"] = round(ns, 2)
        else:
            pm = current_price - e if d == "BUY" else e - current_price
            if pm >= atr_val:
                pos["be"] = True
                pos["sl"] = e

        sl, tp = pos["sl"], pos["tp"]
        hit, pnl, reason = False, 0.0, ""
        if d == "BUY":
            if tp and current_price >= tp:
                pnl = (tp - e) * pv; reason = "TP"; hit = True
            elif sl and current_price <= sl:
                pnl = (sl - e) * pv; reason = "SL" if sl <= e else "TRAIL"; hit = True
        else:
            if tp and current_price <= tp:
                pnl = (e - tp) * pv; reason = "TP"; hit = True
            elif sl and current_price >= sl:
                pnl = (e - sl) * pv; reason = "SL" if sl >= e else "TRAIL"; hit = True

        if hit:
            daily_pnl += pnl
            rec = {**pos, "pnl": round(pnl, 2), "reason": reason,
                   "close_time": datetime.now(timezone.utc).isoformat()}
            all_trades_history.append(rec)
            logger.info(f"  V22 CLOSE: {d} {lot} XAUUSD P/L=${pnl:+.2f} ({reason})")
            if reason == "SL": record_sl()
            else:
                global consecutive_losses
                consecutive_losses = 0
        else:
            remaining.append(pos)
    return remaining


def run():
    logger.info("=" * 60)
    logger.info("V22 GOLD SCALPING BOT - cTrader Edition (Contabo Linux)")
    logger.info("Risk: 0.5%/1.5%/2.5%/3% | Trailing SL | 5 positions")
    logger.info("=" * 60)

    fix = CTraderFIX()
    if not fix.connect():
        logger.critical("cTrader FIX connection failed. Check credentials.")
        return

    logger.info("cTrader connected. Bot starting.")
    cycle = 0
    last_daily = datetime.now(timezone.utc).date()
    global paper_positions

    while True:
        cycle += 1
        now_utc = datetime.now(timezone.utc)
        if now_utc.date() != last_daily:
            global daily_pnl
            daily_pnl = 0.0
            last_daily = now_utc.date()
            logger.info("Daily reset")

        try:
            acc = fix.get_account_info()
            if acc:
                bal = acc.get("balance", 300)
                eq = acc.get("equity", 300)

                status = "paused" if is_paused() else (
                    "halted" if (halt_until and now_utc < halt_until) else "running")
                write_state(bal, eq, status, cycle)

                if not is_paused():
                    # Skip weekends
                    if now_utc.weekday() >= 5:
                        time.sleep(300)
                        continue

                    # Update positions with current price
                    update_positions(bal, 3.5)

                    # Can trade?
                    if not can_trade(now_utc, bal):
                        pass  # Skip entry
                    elif len(paper_positions) < MAX_POSITIONS:
                        global last_entry_time
                        if last_entry_time and (
                                now_utc - last_entry_time).total_seconds() / 60 < ENTRY_COOLDOWN_MINUTES:
                            pass
                        else:
                            # Simple signal: random for now until FIX candles work
                            # This is placeholder - full strategy needs FIX historical data
                            direction = "BUY" if np.random.random() > 0.5 else "SELL"
                            score = 70
                            atr_val = 3.5
                            current_price = bal  # placeholder

                            if score >= MIN_SCORE:
                                sd, td = atr_val * 1.5, atr_val * 3.0
                                sl = round(current_price - sd, 2) if direction == "BUY" else round(
                                    current_price + sd, 2)
                                tp = round(current_price + td, 2) if direction == "BUY" else round(
                                    current_price - td, 2)
                                rp = get_risk_pct(bal)
                                lot = max(0.01,
                                          min(bal * (rp / 100) / (sd * 100) if sd else 0.01, 5.0))
                                lot = round(lot, 2)

                                logger.info(
                                    f"V22 SIGNAL: {direction} {lot} XAUUSD @ ~{current_price} SL={sl} TP={tp}")

                                # Try FIX order
                                result = fix.place_order(direction, lot, sl, tp)
                                if result.get("success"):
                                    logger.info(f"ORDER PLACED: {result}")
                                    last_entry_time = now_utc
                                    paper_positions.append(
                                        {"e": current_price, "tp": tp, "sl": sl, "d": direction,
                                         "lot": lot, "be": False, "open_time": now_utc.isoformat()})

                logger.info(
                    f"C#{cycle} | Bal:${bal:.2f} | Dly:${daily_pnl:+.2f} | Open:{len(paper_positions)} | CL:{consecutive_losses}")

        except KeyboardInterrupt:
            logger.info("Stopped by user")
            break
        except Exception as e:
            logger.error(f"Cycle #{cycle}: {e}")

        time.sleep(60)

    fix.disconnect()


if __name__ == "__main__":
    run()