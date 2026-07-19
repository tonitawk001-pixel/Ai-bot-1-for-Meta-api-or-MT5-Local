"""V22 v4.3 Safe Bot — 1 Week Backtest (Exact Contabo Bot Logic)"""
import os, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf, pandas as pd, numpy as np
warnings.filterwarnings("ignore")
from datetime import timedelta

from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy

BAL = 304.99; SP = 0.50; MIN_SCORE = 45; MAX_POS = 1; MIN_ATR = 1.0
TP_ATR = 3.5; SL_ATR = 1.5; BE_ATR = 2.0; TRAIL_ATR = 0.7
HALT_AFTER = 3; HALT_HOURS = 6; COOLDOWN = 30

print("Downloading M5 and M15 data (60 days)...")
d5 = yf.download("GC=F", interval="5m", period="60d", progress=False)
d15 = yf.download("GC=F", interval="15m", period="60d", progress=False)
for df in [d5, d15]:
    if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
d5 = d5.rename(columns=str.lower).dropna(); d5.index = pd.to_datetime(d5.index, utc=True)
d15 = d15.rename(columns=str.lower).dropna(); d15.index = pd.to_datetime(d15.index, utc=True)

end = d15.index[-1]; s = end - timedelta(days=7)
d15w = d15[(d15.index>=s)&(d15.index<end)].copy()
d5w = d5[(d5.index>=s)&(d5.index<end)].copy()
print(f"1 Week: M15={len(d15w)} candles, M5={len(d5w)} candles")

strategy = GoldScalpingStrategy(); strategy._max_trades_per_day = 50; strategy._max_open_positions = MAX_POS
bal = BAL; closed = []; pos = []; cons = 0; halt = None; dpnl = 0.0; ld = None; le = None; lm15 = None

for i in range(200, len(d15w)):
    ct = d15w.index[i]; p = float(d15w["close"].iloc[i])
    if not (8 <= ct.hour < 22): continue
    d = ct.date()
    if ld is None: ld = d
    if d != ld: dpnl = 0.0; ld = d
    if halt and ct < halt: continue
    if dpnl <= -bal * 0.03: continue
    if lm15 is not None and ct <= lm15: continue

    m15w = d15w.iloc[max(0,i-499):i+1].copy()
    m5u = d5w[d5w.index <= ct]; m5w = m5u.tail(500).copy()
    if len(m15w) < 50 or len(m5w) < 50: continue
    m5i = compute_all_indicators(m5w); m15i = compute_all_indicators(m15w)
    if m5i is None or m15i is None: continue
    if m5i.get("atr") is None or len(m5i["atr"])==0: continue
    atrv = float(m5i["atr"].iloc[-1])
    if atrv < MIN_ATR: lm15 = ct; continue

    surv = []
    for q in pos:
        e,d2,sl,tp,lot = q["entry"],q["dir"],q["sl"],q["tp"],q["lot"]
        pv = lot*100
        if not q.get("be",False) and q.get("be_target"):
            if d2=="BUY" and p>=q["be_target"]: q["be"]=True; q["sl"]=e
            elif d2=="SELL" and p<=q["be_target"]: q["be"]=True; q["sl"]=e
        if q.get("be"):
            ns = p - atrv*TRAIL_ATR if d2=="BUY" else p + atrv*TRAIL_ATR
            if d2=="BUY" and ns>sl+0.5: q["sl"]=round(ns,2)
            elif d2=="SELL" and ns<sl-0.5: q["sl"]=round(ns,2)
        sl,tp = q["sl"],q["tp"]
        hit=False; pnl=0; r=""
        if d2=="BUY":
            if tp and p>=tp: pnl=(tp-e)*pv; r="TP"; hit=True
            elif sl and p<=sl: pnl=(sl-e)*pv; r="TRAIL" if sl>e else "SL"; hit=True
        else:
            if tp and p<=tp: pnl=(e-tp)*pv; r="TP"; hit=True
            elif sl and p>=sl: pnl=(e-sl)*pv; r="TRAIL" if sl<e else "SL"; hit=True
        if hit:
            pnl -= SP*lot*100; dpnl += pnl
            q["pnl"]=pnl; q["reason"]=r; q["close_price"]=p; closed.append(q)
            if r=="SL" and pnl<0: cons+=1
            else: cons=0
        else: surv.append(q)
    pos = surv
    for t in list(closed):
        if t.get("_p"): continue
        t["_p"]=True; bal+=t["pnl"]
    if cons >= HALT_AFTER and halt is None: halt = ct+timedelta(hours=HALT_HOURS); cons=0
    if len(pos) >= MAX_POS: lm15=ct; continue
    if le and (ct-le).total_seconds()/60 < COOLDOWN: lm15=ct; continue

    em1={"rsi":pd.Series([50]),"emas":pd.DataFrame(),"macd":pd.Series([0])}
    try:
        r = strategy.analyze(m1_indicators=em1, m5_indicators=m5i, m15_indicators=m15i,
            m1_ohlcv=m5w.tail(20), m5_ohlcv=m5w, m15_ohlcv=m15w, news_context=None)
    except: lm15=ct; continue
    direction = r.get("direction","NONE"); score = r.get("setup_score",0)
    if direction=="NONE" or score<MIN_SCORE: lm15=ct; continue

    try:
        if direction=="BUY" and not (m5i["rsi"].iloc[-1]>40 and m15i["rsi"].iloc[-1]>40): lm15=ct; continue
        if direction=="SELL" and not (m5i["rsi"].iloc[-1]<60 and m15i["rsi"].iloc[-1]<60): lm15=ct; continue
    except: pass
    cs = m15w["close"].values
    if len(cs)>=200:
        e200 = pd.Series(cs).ewm(200,adjust=False).mean().values
        if len(e200)>=10:
            rising = e200[-1] > e200[-10]
            if direction=="BUY" and not rising: lm15=ct; continue
            if direction=="SELL" and rising: lm15=ct; continue

    sd = atrv*SL_ATR; td = atrv*TP_ATR
    sl = round(p-sd,2) if direction=="BUY" else round(p+sd,2)
    tp = round(p+td,2) if direction=="BUY" else round(p-td,2)
    rp = 0.02; lot = max(0.01, min(round((bal*rp)/(sd*100)/0.01)*0.01, 10.0))
    bt = p + (atrv*BE_ATR if direction=="BUY" else -atrv*BE_ATR)
    pos.append({"entry":p,"sl":sl,"tp":tp,"lot":lot,"dir":direction,"open_time":ct,"score":score,"be_target":bt,"be":False})
    le = ct; lm15 = ct

tp=0; wc=0; lc=0; wp=[]; lp=[]; dt={}
for t in closed:
    pnl=t["pnl"]; tp+=pnl
    if pnl>0: wc+=1; wp.append(pnl)
    else: lc+=1; lp.append(pnl)
    dk=t["open_time"].date()
    dt[dk]=dt.get(dk,0)+1

print(); print("="*60)
print("  V22 v4.3 SAFE BOT — 1 WEEK (Jul 9-16)")
print("  Exact same logic as Contabo bot")
print("="*60)
print(f"  Starting:    ${BAL:.2f}")
print(f"  Final:       ${BAL+tp:.2f}")
print(f"  Net P&L:     ${tp:+.2f} ({(tp/BAL)*100:+.1f}%)")
print(f"  Total Trades: {len(closed)} ({len(closed)//5}/day)")
print(f"  Wins:        {wc} ({wc/len(closed)*100:.0f}%)" if closed else "")
print(f"  Losses:      {lc} ({lc/len(closed)*100:.0f}%)" if closed else "")
if wp and lp:
    print(f"  Avg Win:     ${(sum(wp)/len(wp)):.2f}")
    print(f"  Avg Loss:    ${(sum(lp)/len(lp)):.2f}")
    print(f"  Profit Factor: {abs(sum(wp)/sum(lp)):.2f}")
print(f"\n  Daily Breakdown:")
for d in sorted(dt):
    day_trades = dt[d]
    day_pnl = sum(t["pnl"] for t in closed if t["open_time"].date()==d)
    print(f"  {str(d)[5:]:<8} {day_trades:>2} trades  ${day_pnl:+.2f}")