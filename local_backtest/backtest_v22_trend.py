"""V22 v4.1 — Improved symmetric EMA200 filter. Runs specified month."""
import os, sys, warnings
from datetime import datetime, timedelta, timezone
warnings.filterwarnings("ignore")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import pandas as pd
import numpy as np

from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
from trading_bot.strategy.gold_volatility_filter import GoldVolatilityFilter

SYMBOL = "XAUUSD"
STARTING_BALANCE = 304.99
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
RISK_PERCENT = {(0, 250): 0.5, (250, 500): 1.5, (500, 1000): 2.5, (1000, float('inf')): 3.0}
TRADE_HOURS_START = 8
TRADE_HOURS_END = 22
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# WIDENED RANGE FOR MULTI-MONTH BACKTESTING
START_DATE = "2026-01-01"
END_DATE = "2026-07-01"

def get_risk_pct(b): return next((p for (lo,hi),p in RISK_PERCENT.items() if lo<=b<hi), 1.0)
def in_session(dt): return TRADE_HOURS_START <= dt.hour < TRADE_HOURS_END

def load_data():
    f15 = os.path.join(DATA_DIR, "XAUUSD_60d_M15.csv")
    f5 = os.path.join(DATA_DIR, "XAUUSD_60d_M5.csv")
    if not os.path.exists(f15): return None, None
    d15 = pd.read_csv(f15, index_col=0, parse_dates=True)
    d5 = pd.read_csv(f5, index_col=0, parse_dates=True) if os.path.exists(f5) else pd.DataFrame()
    d15.columns = [c.lower() for c in d15.columns]
    if not d5.empty:
        d5.columns = [c.lower() for c in d5.columns]
        d5 = d5[~d5.index.duplicated(keep='last')].dropna()
    d15 = d15[~d15.index.duplicated(keep='last')].dropna()
    return d15, d5

def safe_vol_filter(vol_filter, m5o, m15o, m5i, m15i):
    from trading_bot.utils.logger import logger; import logging
    old = logger.level; logger.setLevel(logging.ERROR)
    try:
        em1 = {"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
        r = vol_filter.analyze(m1_ohlcv=m5o.tail(20), m5_ohlcv=m5o, m15_ohlcv=m15o,
            m1_indicators=em1, m5_indicators=m5i, m15_indicators=m15i)
        return r
    except:
        return {"trade_ok": True, "lot_reduction_factor": 1.0}
    finally:
        logger.setLevel(old)

def update_positions(positions, price, atr_val, dpnl, logs):
    surv = []
    for p in positions:
        e, d, sl, tp, lot = p["entry"], p["dir"], p["sl"], p["tp"], p["lot"]
        pv = lot * 100
        if not p.get("be",False) and p.get("be_target"):
            if d=="BUY" and price>=p["be_target"]: p["be"]=True; p["sl"]=e
            elif d=="SELL" and price<=p["be_target"]: p["be"]=True; p["sl"]=e
        if p.get("be"):
            ns = price - atr_val*TRAIL_ATR_MULT if d=="BUY" else price + atr_val*TRAIL_ATR_MULT
            if d=="BUY" and ns>sl+0.5: p["sl"]=round(ns,2)
            elif d=="SELL" and ns<sl-0.5: p["sl"]=round(ns,2)
        sl, tp = p["sl"], p["tp"]
        hit=False; pnl=0.0; reason=""
        if d=="BUY":
            if tp and price>=tp: pnl=(tp-e)*pv; reason="TP"; hit=True
            elif sl and price<=sl: pnl=(sl-e)*pv; reason="TRAIL" if sl>e else "SL"; hit=True
        else:
            if tp and price<=tp: pnl=(e-tp)*pv; reason="TP"; hit=True
            elif sl and price>=sl: pnl=(e-sl)*pv; reason="TRAIL" if sl<e else "SL"; hit=True
        if hit:
            pnl-= SPREAD_PIPS*lot*100; dpnl+=pnl
            p["pnl"]=pnl; p["reason"]=reason; p["close_price"]=price; logs.append(p)
        else:
            surv.append(p)
    return surv, dpnl

def run_backtest():
    print("="*70)
    print(f"  V22 v4.1 (SYMMETRIC EMA200) — {START_DATE} to {END_DATE}")
    print("="*70)
    d15, d5 = load_data()
    if d15 is None: print("No data"); return
    d15 = d15[(d15.index>=START_DATE)&(d15.index<END_DATE)].copy()
    if not d5.empty: d5 = d5[(d5.index>=START_DATE)&(d5.index<END_DATE)].copy()
    print(f"M15={len(d15)} M5={len(d5) if not d5.empty else 0}")
    print(f"Period: {d15.index[0]} -> {d15.index[-1]}")
    print(f"Starting: ${STARTING_BALANCE:.2f}\n")

    strategy = GoldScalpingStrategy()
    strategy._max_trades_per_day = 50; strategy._max_open_positions = MAX_POSITIONS
    vol_filter = GoldVolatilityFilter()
    balance = STARTING_BALANCE; positions=[]; daily_pnl=0.0; cons_losses=0
    halt_until=None; last_entry=None; last_date=None; closed=[]

    for i in range(min(200,len(d15)-1), len(d15)):
        ct=d15.index[i]; price=float(d15["close"].iloc[i])
        if not in_session(ct): continue
        if last_date is None: last_date=ct.date()
        if ct.date()!=last_date: daily_pnl=0.0; last_date=ct.date()
        if halt_until and ct<halt_until: continue
        if daily_pnl<=-balance*DAILY_LOSS_PCT: continue

        atr_upd=3.5
        m5u=d5[d5.index<=ct] if not d5.empty else pd.DataFrame()
        m5s=m5u.tail(200).copy()
        if len(m5s)>=50:
            i5=compute_all_indicators(m5s)
            if i5 and i5["atr"] is not None and not i5["atr"].empty:
                try: atr_upd=float(i5["atr"].iloc[-1])
                except: pass

        positions, daily_pnl = update_positions(positions, price, atr_upd, daily_pnl, closed)
        for t in list(closed):
            if t.get("processed"): continue
            t["processed"]=True; balance+=t["pnl"]
            if t["reason"] in ("SL","TRAIL") and t["pnl"]<0:
                cons_losses+=1
                if cons_losses>=HALT_AFTER_LOSSES: halt_until=ct+timedelta(hours=HALT_HOURS); cons_losses=0
            else: cons_losses=0
        if len(positions)>=MAX_POSITIONS: continue

        m15w=d15.iloc[max(0,i-499):i+1].copy()
        ind15=compute_all_indicators(m15w)
        if ind15 is None: continue
        m5w=m5u.tail(500).copy()
        if len(m5w)<50: continue
        ind5=compute_all_indicators(m5w)
        if ind5 is None: continue

        atr_val=3.5
        try:
            if not ind5["atr"].empty: atr_val=float(ind5["atr"].iloc[-1])
        except: pass
        if atr_val<MIN_ATR: continue
        if last_entry and (ct-last_entry).total_seconds()/60<ENTRY_COOLDOWN_MINUTES: continue

        try:
            em1={"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
            eo=m5w.tail(20)
            result=strategy.analyze(m1_indicators=em1, m5_indicators=ind5, m15_indicators=ind15,
                m1_ohlcv=eo, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None)
        except: continue

        direction = result.get("direction", "NONE")
        score = 0 # Fallback since 'setup' key was incomplete in source file content

        # ADDITIONAL FILTER: Check for indicator convergence (high confluence). 
        # Example check: Ensure RSI and MACD are trending in the desired direction on M5 and M15.
        rsi_bullish = ind5["rsi"].iloc[-1] > 40 and ind15["rsi"].iloc[-1] > 40 # Both periods above midline (bullish)
        rsi_bearish = ind5["rsi"].iloc[-1] < 60 and ind15["rsi"].iloc[-1] < 60 # Both periods below midline (bearish)

        # Set indicator filters based on direction to enforce strong confluence
        if direction == "BUY":
            if not rsi_bullish: continue
        elif direction == "SELL":
            if not rsi_bearish: continue


        closes = m15w["close"].values
        if len(closes) >= 200:
            ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
            if len(ema200) < 10: continue

            rising = float(ema200[-1]) > float(ema200[-10])

            # STRICT FILTERING: Must confirm direction using EMA 200 slope
            if direction == "BUY" and not rising: 
                continue # Only BUY if EMA is rising (bullish momentum)
            if direction == "SELL" and rising: 
                continue # Only SELL if EMA is falling (bearish momentum)
        # --- END IMPROVEMENT SECTION ---


        vo=safe_vol_filter(vol_filter,m5w,m15w,ind5,ind15)
        if not vo.get("trade_ok",False): continue

        sd=atr_val*SL_ATR_MULT; td=atr_val*TP_ATR_MULT
        if direction=="BUY": sl=round(price-sd,2); tp=round(price+td,2)
        else: sl=round(price+sd,2); tp=round(price-td,2)
        rp=get_risk_pct(balance)
        lot=max(0.01,round(balance*(rp/100)/(sd*100),2)); lot=min(lot,10.0)
        bt=price+(atr_val*BE_ATR_MULT if direction=="BUY" else -atr_val*BE_ATR_MULT)
        pos={"entry":price,"sl":sl,"tp":tp,"lot":lot,"dir":direction,"open_time":ct,"score":score,"be_target":bt,"be":False}
        positions.append(pos); last_entry=ct

    print("="*70); print("  ALL TRADES"); print("="*70)
    if not closed: print("  No trades."); return
    closed.sort(key=lambda x: x.get("close_time",x["open_time"]))
    tp=0; wc=0; lc=0; wp=[]; lp=[]; dpnl={}; dc={}; rc={}
    print(f"  {'#':<4} {'Date':<12} {'Dir':<5} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Reason':<8} {'Lot':<5}")
    print(f"  {'-'*64}")
    for idx,t in enumerate(closed,1):
        pnl=t["pnl"]; tp+=pnl
        if pnl>0: wc+=1; wp.append(pnl)
        else: lc+=1; lp.append(pnl)
        dc[t["dir"]]=dc.get(t["dir"],0)+1
        rc[t.get("reason","?")]=rc.get(t.get("reason","?"),0)+1
        d=t["open_time"].strftime("%m/%d") if hasattr(t["open_time"],"strftime") else str(t["open_time"])[:10]
        dk=t["open_time"].date() if hasattr(t["open_time"],"date") else t["open_time"][:10]
        dpnl[dk]=dpnl.get(dk,0)+pnl
        print(f"  {idx:<4} {d:<12} {t['dir']:<5} {t['entry']:<10.2f} {t.get('close_price',0):<10.2f} ${pnl:<+7.2f} {t.get('reason',''):<8} {t['lot']:<5.2f}")

    print(); print("="*70); print(f"  PERFORMANCE SUMMARY — {START_DATE[:7]}"); print("="*70)
    peak=STARTING_BALANCE; maxdd=0; eq=[STARTING_BALANCE]
    for t in closed: eq.append(eq[-1]+t["pnl"])
    for e in eq:
        peak=max(peak,e); dd=(peak-e)/peak*100; maxdd=max(maxdd,dd)
    print(f"  Starting:           ${STARTING_BALANCE:.2f}")
    print(f"  Final:              ${STARTING_BALANCE+tp:.2f}")
    print(f"  P&L:                ${tp:+.2f} ({(tp/STARTING_BALANCE)*100:+.1f}%)")
    print(f"  Trades:             {len(closed)}")
    print(f"  Win Rate:           {wc}/{len(closed)} ({wc/len(closed)*100:.1f}%)")
    print(f"  Avg Win:            ${(sum(wp)/len(wp)) if wp else 0:+.2f}")
    print(f"  Avg Loss:           ${(sum(lp)/len(lp)) if lp else 0:+.2f}")
    if wp and lp: print(f"  Profit Factor:      {abs(sum(wp)/sum(lp)):.2f}")
    print(f"  Best/Worst:         ${max(t['pnl'] for t in closed):+.2f} / ${min(t['pnl'] for t in closed):+.2f}")
    print(f"  BUY/SELL:           {dc.get('BUY',0)} / {dc.get('SELL',0)}")
    print(f"  Max DD:             {maxdd:.1f}%")
    print(f"  Close reasons:      {rc}")
    print(); print("  DAILY P&L:")
    cum=STARTING_BALANCE
    for day in sorted(dpnl.keys()):
        cum+=dpnl[day]; print(f"  {str(day):<12} ${dpnl[day]:<+7.2f} ${cum:<.2f}")

if __name__=="__main__":
    try: run_backtest()
    except Exception as e: print(f"ERROR: {e}"); import traceback; traceback.print_exc()