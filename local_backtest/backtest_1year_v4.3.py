"""V22 v4.3 — Full 1-Year Backtest on Resampled H1→M15 Data (Exact Live Logic)"""
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

# === V22 v4.3 CONFIG ===
SYMBOL = "XAUUSD"
STARTING_BALANCE = 304.99
MIN_SCORE = 45; MAX_POSITIONS = 1; MIN_ATR = 1.0
TP_ATR_MULT = 3.5; TP_ATR_MULT_TREND = 5.0; SL_ATR_MULT = 1.5
BE_ATR_MULT = 2.0; TRAIL_ATR_MULT = 0.7
HALT_AFTER_LOSSES = 3; HALT_HOURS = 6; ENTRY_COOLDOWN_MINUTES = 30
DAILY_LOSS_PCT = 0.03; SPREAD_PIPS = 0.50
ADX_TREND_THRESHOLD = 25
RISK_PERCENT_FLAT = 2.0  # v4.3: 2% flat risk
TRADE_HOURS_START = 8; TRADE_HOURS_END = 22
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# 1 year period
START_DATE = "2025-07-15"
END_DATE = "2026-07-15"

def in_session(dt): return TRADE_HOURS_START <= dt.hour < TRADE_HOURS_END

# ADX
def compute_adx(high, low, close, period=14):
    if len(close) < period * 2:
        return pd.Series([np.nan] * len(close), index=close.index)
    high = high.astype(float); low = low.astype(float); close = close.astype(float)
    tr = pd.concat([(high-low).abs(), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    up_move = high - high.shift(); down_move = low.shift() - low
    plus_dm = np.where((up_move>down_move)&(up_move>0), up_move, 0.0)
    minus_dm = np.where((down_move>up_move)&(down_move>0), down_move, 0.0)
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=close.index).ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm, index=close.index).ewm(span=period, adjust=False).mean() / atr
    dx = 100 * (plus_di-minus_di).abs() / (plus_di+minus_di).replace(0, np.nan)
    return dx.ewm(span=period, adjust=False).mean()

# v4.3: Lot sizing (2% flat risk)
def calc_lot(balance, sl_dist):
    if sl_dist <= 0 or balance <= 0: return 0.01
    raw = (balance * 0.02) / (sl_dist * 100)
    raw = round(raw / 0.01) * 0.01
    return max(0.01, min(raw, 10.0))

# Load + resample H1 to M15
def load_and_resample():
    f = os.path.join(DATA_DIR, "XAUUSD_1y_H1.csv")
    if not os.path.exists(f):
        print(f"[!] Data not found at {f}")
        return None, None
    
    df_h1 = pd.read_csv(f, index_col=0, parse_dates=True)
    df_h1.columns = [c.lower() for c in df_h1.columns]
    df_h1.index = pd.to_datetime(df_h1.index, utc=True)
    df_h1 = df_h1[~df_h1.index.duplicated(keep='last')].sort_index()
    
    print(f"H1 data: {len(df_h1)} candles, {df_h1.index[0]} -> {df_h1.index[-1]}")
    
    # Resample H1 to M15 using linear interpolation
    idx_m15 = pd.date_range(start=df_h1.index[0], end=df_h1.index[-1] + pd.Timedelta(hours=1), freq='15min', tz='UTC')
    idx_m15 = idx_m15[idx_m15 < df_h1.index[-1] + pd.Timedelta(hours=1)]
    
    d15 = pd.DataFrame(index=idx_m15, columns=['open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close']:
        d15[col] = np.nan
        d15.loc[df_h1.index, col] = df_h1[col].values
        d15[col] = d15[col].interpolate(method='linear')
    d15['volume'] = 0
    d15['high'] = d15[['open', 'close']].max(axis=1)
    d15['low'] = d15[['open', 'close']].min(axis=1)
    
    # Generate M5 from M15 (forward fill)
    idx_m5 = pd.date_range(start=d15.index[0], end=d15.index[-1] + pd.Timedelta(minutes=15), freq='5min', tz='UTC')
    idx_m5 = idx_m5[idx_m5 < d15.index[-1] + pd.Timedelta(minutes=15)]
    d5 = pd.DataFrame(index=idx_m5, columns=['open', 'high', 'low', 'close', 'volume'])
    for col in ['open', 'high', 'low', 'close']:
        d5[col] = np.nan
        for m15_time in d15.index:
            mask = (d5.index >= m15_time) & (d5.index < m15_time + pd.Timedelta(minutes=15))
            d5.loc[mask, col] = d15.loc[m15_time, col]
        d5[col] = d5[col].ffill()
    d5['volume'] = 0
    
    # Filter to our date range
    d15 = d15[(d15.index >= START_DATE) & (d15.index < END_DATE)].copy()
    d5 = d5[(d5.index >= START_DATE) & (d5.index < END_DATE)].copy()
    
    # Convert tz-naive to UTC
    if d15.index.tz is None: d15.index = d15.index.tz_localize('UTC')
    if d5.index.tz is None: d5.index = d5.index.tz_localize('UTC')
    
    return d15, d5

def run_backtest():
    print("=" * 80)
    print("  V22 v4.3 — 1 YEAR BACKTEST (Jul 2025 - Jul 2026)")
    print("  Exact live logic: 2% flat risk | ADX dynamic TP | live breakeven")
    print("=" * 80)
    
    d15, d5 = load_and_resample()
    if d15 is None or len(d15) < 500:
        print("  [!] Insufficient data"); return
    
    print(f"M15={len(d15)} M5={len(d5)}")
    print(f"Period: {d15.index[0]} -> {d15.index[-1]}")
    print(f"Starting: ${STARTING_BALANCE:.2f}\n")

    strategy = GoldScalpingStrategy()
    strategy._max_trades_per_day = 50; strategy._max_open_positions = MAX_POSITIONS
    vol_filter = GoldVolatilityFilter()
    balance = STARTING_BALANCE; positions=[]; daily_pnl=0.0; cons_losses=0
    halt_until=None; last_entry=None; last_date=None; closed=[]
    total_entries = 0; dynamic_tp_count = 0

    for i in range(min(200, len(d15)-1), len(d15)):
        ct = d15.index[i]; price = float(d15["close"].iloc[i])
        if not in_session(ct): continue
        if last_date is None: last_date = ct.date()
        if ct.date() != last_date: daily_pnl = 0.0; last_date = ct.date()
        if halt_until and ct < halt_until: continue
        if daily_pnl <= -balance * DAILY_LOSS_PCT: continue

        atr_upd = 3.5
        m5u = d5[d5.index <= ct] if not d5.empty else pd.DataFrame()
        m5s = m5u.tail(200).copy()
        if len(m5s) >= 50:
            i5 = compute_all_indicators(m5s)
            if i5 and i5["atr"] is not None and not i5["atr"].empty:
                try: atr_upd = float(i5["atr"].iloc[-1])
                except: pass

        # Update positions
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
                pnl -= SPREAD_PIPS*lot*100; daily_pnl += pnl
                p["pnl"]=pnl; p["reason"]=reason; p["close_price"]=price; closed.append(p)
                if reason == "SL": cons_losses += 1
                else: cons_losses = 0
            else:
                surv.append(p)
        positions = surv
        
        # Process closed trades
        for t in list(closed):
            if t.get("processed"): continue
            t["processed"] = True; balance += t["pnl"]
        
        if len(positions) >= MAX_POSITIONS: continue
        
        # Cooldown check
        if last_entry and (ct - last_entry).total_seconds()/60 < ENTRY_COOLDOWN_MINUTES: continue

        m15w = d15.iloc[max(0,i-499):i+1].copy()
        ind15 = compute_all_indicators(m15w)
        if ind15 is None: continue
        m5w = m5u.tail(500).copy()
        if len(m5w) < 50 or m5w.isna().any().any(): continue
        ind5 = compute_all_indicators(m5w)
        if ind5 is None: continue

        atr_val = 3.5
        try:
            if not ind5["atr"].empty: atr_val = float(ind5["atr"].iloc[-1])
        except: pass
        if atr_val < MIN_ATR: continue

        # ADX
        try:
            adx_series = compute_adx(m5w["high"], m5w["low"], m5w["close"], period=14)
            adx_val = float(adx_series.iloc[-1]) if not pd.isna(adx_series.iloc[-1]) else 0
        except: adx_val = 0
        tp_mult = TP_ATR_MULT_TREND if adx_val >= ADX_TREND_THRESHOLD else TP_ATR_MULT

        try:
            em1={"rsi": pd.Series([50]), "emas": pd.DataFrame(), "macd": pd.Series([0])}
            eo=m5w.tail(20)
            result=strategy.analyze(m1_indicators=em1, m5_indicators=ind5, m15_indicators=ind15,
                m1_ohlcv=eo, m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None)
        except: continue

        direction = result.get("direction","NONE")
        score = result.get("setup_score",0)
        if direction == "NONE" or score < MIN_SCORE: continue

        # RSI
        try:
            if direction=="BUY" and not (ind5["rsi"].iloc[-1]>40 and ind15["rsi"].iloc[-1]>40): continue
            if direction=="SELL" and not (ind5["rsi"].iloc[-1]<60 and ind15["rsi"].iloc[-1]<60): continue
        except: pass

        # EMA200
        closes = m15w["close"].values
        if len(closes) >= 200:
            ema200 = pd.Series(closes).ewm(200, adjust=False).mean().values
            if len(ema200) >= 10:
                rising = float(ema200[-1]) > float(ema200[-10])
                if direction=="BUY" and not rising: continue
                if direction=="SELL" and rising: continue

        # Volatility filter
        try:
            vo = vol_filter.analyze(m1_ohlcv=eo, m5_ohlcv=m5w, m15_ohlcv=m15w,
                m1_indicators=em1, m5_indicators=ind5, m15_indicators=ind15)
            if not vo.get("trade_ok", False): continue
        except: pass

        # Entry
        sd = atr_val * SL_ATR_MULT; td = atr_val * tp_mult
        if direction=="BUY": sl=round(price-sd,2); tp=round(price+td,2)
        else: sl=round(price+sd,2); tp=round(price-td,2)

        lot = calc_lot(balance, sd)
        bt = price + (atr_val*BE_ATR_MULT if direction=="BUY" else -atr_val*BE_ATR_MULT)

        total_entries += 1
        if adx_val >= ADX_TREND_THRESHOLD: dynamic_tp_count += 1

        positions.append({"entry":price,"sl":sl,"tp":tp,"lot":lot,"dir":direction,"open_time":ct,"score":score,"be_target":bt,"be":False})
        last_entry = ct

    print("="*80); print("  ALL TRADES"); print("="*80)
    if not closed: print("  No trades."); return
    closed.sort(key=lambda x: x.get("close_time",x["open_time"]))
    tp=0; wc=0; lc=0; wp=[]; lp=[]; dpnl={}; dc={}; rc={}
    print(f"  {'#':<4} {'Date':<12} {'Dir':<5} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Reason':<8} {'Lot':<8}")
    print(f"  {'-'*70}")
    for idx,t in enumerate(closed,1):
        pnl=t["pnl"]; tp+=pnl
        if pnl>0: wc+=1; wp.append(pnl)
        else: lc+=1; lp.append(pnl)
        dc[t["dir"]]=dc.get(t["dir"],0)+1
        rc[t.get("reason","?")]=rc.get(t.get("reason","?"),0)+1
        dk=t["open_time"].date() if hasattr(t["open_time"],"date") else str(t["open_time"])[:10]
        dpnl[dk]=dpnl.get(dk,0)+pnl
        d=t["open_time"].strftime("%m/%d") if hasattr(t["open_time"],"strftime") else str(t["open_time"])[:10]
        print(f"  {idx:<4} {d:<12} {t['dir']:<5} {t['entry']:<10.2f} {t.get('close_price',0):<10.2f} ${pnl:<+7.2f} {t.get('reason',''):<8} {t['lot']:<8.2f}")

    print(); print("="*80); print("  V22 v4.3 — 1 YEAR PERFORMANCE (Jul 2025 - Jul 2026)"); print("="*80)
    peak=STARTING_BALANCE; maxdd=0; eq=[STARTING_BALANCE]
    for t in closed: eq.append(eq[-1]+t["pnl"])
    for e in eq:
        peak=max(peak,e); dd=(peak-e)/peak*100; maxdd=max(maxdd,dd)

    print(f"  Starting:           ${STARTING_BALANCE:.2f}")
    print(f"  Final Balance:      ${STARTING_BALANCE+tp:.2f}")
    print(f"  Net Profit:         ${tp:+.2f} ({(tp/STARTING_BALANCE)*100:+.1f}%)")
    print(f"  Total Trades:       {len(closed)}")
    print(f"  Wins:               {wc} ({wc/len(closed)*100:.1f}%)")
    print(f"  Losses:             {lc} ({lc/len(closed)*100:.1f}%)")
    print(f"  Avg Win:            ${(sum(wp)/len(wp)) if wp else 0:+.2f}")
    print(f"  Avg Loss:           ${(sum(lp)/len(lp)) if lp else 0:+.2f}")
    if wp and lp: print(f"  Profit Factor:      {abs(sum(wp)/sum(lp)):.2f}")
    print(f"  Best Trade:         ${max(t['pnl'] for t in closed):+.2f}")
    print(f"  Worst Trade:        ${min(t['pnl'] for t in closed):+.2f}")
    print(f"  BUY / SELL:         {dc.get('BUY',0)} / {dc.get('SELL',0)}")
    print(f"  Max Drawdown:       {maxdd:.1f}%")
    print(f"  Close Reasons:      {rc}")

    print(f"\n  === V22 v4.3 STATS ===")
    print(f"  Risk Model:         2% Flat of Balance")
    print(f"  Total Entries:      {total_entries}")
    print(f"  Dynamic TP (ADX≥25):{dynamic_tp_count} ({dynamic_tp_count/total_entries*100:.1f}%)" if total_entries else "  0")
    print(f"  Weekly Trades Avg:  {len(closed)/52:.1f}")
    print(f"  Monthly Trades Avg: {len(closed)/12:.1f}")

    # Monthly breakdown
    print(f"\n  === MONTHLY P&L ===")
    cum = STARTING_BALANCE
    monthly = {}
    for day in sorted(dpnl.keys()):
        month_key = str(day)[:7]
        monthly[month_key] = monthly.get(month_key, 0) + dpnl[day]
    for month in sorted(monthly.keys()):
        print(f"  {month:<10} ${monthly[month]:<+8.2f}")

if __name__=="__main__":
    try: run_backtest()
    except Exception as e: print(f"ERROR: {e}"); import traceback; traceback.print_exc()