"""V22 v4.1 — July Uptrend Test"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
from trading_bot.strategy.gold_volatility_filter import GoldVolatilityFilter

BAL=304.99; DAILY_LOSS=0.03; SPREAD=0.50; COOLDOWN=30
RISK={(0,250):0.5,(250,500):1.5,(500,1000):2.5,(1000,float('inf')):3.0}
START="2026-07-01"; END="2026-07-14"
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load():
    d15 = pd.read_csv(os.path.join(DIR,"XAUUSD_60d_M15.csv"), index_col=0, parse_dates=True)
    d5 = pd.read_csv(os.path.join(DIR,"XAUUSD_60d_M5.csv"), index_col=0, parse_dates=True)
    for df in [d15, d5]:
        df.columns = [c.lower() for c in df.columns]
    return d15, d5

d15, d5 = load()
d15 = d15[(d15.index>=START)&(d15.index<END)].copy()
d5 = d5[(d5.index>=START)&(d5.index<END)].copy()
print(f"July Backtest: M15={len(d15)} M5={len(d5)}")

s = GoldScalpingStrategy(); s._max_trades_per_day=50; s._max_open_positions=1
vf = GoldVolatilityFilter()
bal=BAL; pos=[]; dpnl=0.0; cons=0; hu=None; le=None; ld=None; closed=[]

for i in range(200, len(d15)):
    ct=d15.index[i]; p=float(d15["close"].iloc[i])
    if not (8<=ct.hour<22): continue
    if ld is None: ld=ct.date()
    if ct.date()!=ld: dpnl=0.0; ld=ct.date()
    if hu and ct<hu: continue
    if dpnl<=-bal*DAILY_LOSS: continue

    m5u=d5[d5.index<=ct]; m5s=m5u.tail(200).copy()
    atr_upd=3.5
    if len(m5s)>=50:
        i5=compute_all_indicators(m5s)
        if i5 and i5["atr"] is not None and len(i5["atr"])>0: atr_upd=float(i5["atr"].iloc[-1])

    # Update positions
    surv=[]
    for x in pos:
        e,d,s,t,l=x["entry"],x["dir"],x["sl"],x["tp"],x["lot"]; pv=l*100
        if not x.get("be") and x.get("be_target"):
            if d=="BUY" and p>=x["be_target"]: x["be"]=True; x["sl"]=e
            elif d=="SELL" and p<=x["be_target"]: x["be"]=True; x["sl"]=e
        if x.get("be"):
            ns=p-atr_upd*0.7 if d=="BUY" else p+atr_upd*0.7
            if d=="BUY" and ns>s+0.5: x["sl"]=round(ns,2)
            elif d=="SELL" and ns<s-0.5: x["sl"]=round(ns,2)
        s,t=x["sl"],x["tp"]; hit=False; pnl=0.0; r=""
        if d=="BUY":
            if t and p>=t: pnl=(t-e)*pv; r="TP"; hit=True
            elif s and p<=s: pnl=(s-e)*pv; r="TRAIL" if s>e else "SL"; hit=True
        else:
            if t and p<=t: pnl=(e-t)*pv; r="TP"; hit=True
            elif s and p>=s: pnl=(e-s)*pv; r="TRAIL" if s<e else "SL"; hit=True
        if hit:
            pnl-=SPREAD*l*100; dpnl+=pnl; x["pnl"]=pnl; x["reason"]=r; x["close_price"]=p; closed.append(x)
        else: surv.append(x)
    pos=surv

    for t in list(closed):
        if t.get("pro"): continue
        t["pro"]=True; bal+=t["pnl"]
        if t.get("reason") in ("SL","TRAIL") and t["pnl"]<0:
            cons+=1
            if cons>=3: hu=ct+timedelta(hours=6); cons=0
        else: cons=0
    if len(pos)>=1: continue

    m15w=d15.iloc[max(0,i-499):i+1].copy()
    ind15=compute_all_indicators(m15w)
    if ind15 is None: continue
    m5w=m5u.tail(500).copy()
    if len(m5w)<50: continue
    ind5=compute_all_indicators(m5w)
    if ind5 is None: continue

    atv=3.5
    if ind5["atr"] is not None and len(ind5["atr"])>0: atv=float(ind5["atr"].iloc[-1])
    if atv<1.0: continue
    if le and (ct-le).total_seconds()/60<COOLDOWN: continue

    try:
        em1={"rsi":pd.Series([50]),"emas":pd.DataFrame(),"macd":pd.Series([0])}
        eo=m5w.tail(20)
        r=s.analyze(m1_indicators=em1,m5_indicators=ind5,m15_indicators=ind15,
            m1_ohlcv=eo,m5_ohlcv=m5w,m15_ohlcv=m15w,news_context=None)
    except: continue
    d=r.get("direction","NONE"); sc=r.get("setup_score",0)
    if d=="NONE" or sc<45: continue

    # Symmetric EMA200
    cl=m15w["close"].values
    if len(cl)>=200:
        e200=pd.Series(cl).ewm(200,adjust=False).mean().values
        if len(e200)>=10:
            ris=float(e200[-1])>float(e200[-10])
            if d=="BUY" and not ris: continue
            if d=="SELL" and ris: continue

    try:
        vo=vf.analyze(m1_ohlcv=eo,m5_ohlcv=m5w,m15_ohlcv=m15w,
            m1_indicators=em1,m5_indicators=ind5,m15_indicators=ind15)
        if not vo.get("trade_ok",True): continue
    except: pass

    sd=atv*1.5; td=atv*3.5
    sl=round(p-sd,2) if d=="BUY" else round(p+sd,2)
    tp=round(p+td,2) if d=="BUY" else round(p-td,2)
    rp=next((v for (lo,hi),v in RISK.items() if lo<=bal<hi),1.0)
    lot=max(0.01,round(bal*(rp/100)/(sd*100),2)); lot=min(lot,10.0)
    bt=p+(atv*2.0 if d=="BUY" else -atv*2.0)
    pos.append({"entry":p,"sl":sl,"tp":tp,"lot":lot,"dir":d,"open_time":ct,"score":sc,"be_target":bt,"be":False})
    le=ct

if not closed: print("No trades in July"); exit()
tp=sum(t["pnl"] for t in closed)
w=[t for t in closed if t["pnl"]>0]; l=[t for t in closed if t["pnl"]<=0]
print(f"\nTotal P&L: ${tp:+.2f} ({tp/BAL*100:.1f}%)")
print(f"Trades: {len(closed)} | Win: {len(w)/len(closed)*100:.1f}% ({len(w)}W/{len(l)}L)")
print(f"Avg W: ${sum(x['pnl'] for x in w)/len(w):+.2f}" if w else "", f"Avg L: ${sum(x['pnl'] for x in l)/len(l):+.2f}" if l else "")
print(f"SELL: {len([x for x in closed if x['dir']=='SELL'])} | BUY: {len([x for x in closed if x['dir']=='BUY'])}")
peak=BAL; mdd=0; eq=[BAL]
for t in closed: eq.append(eq[-1]+t["pnl"])
for e in eq: peak=max(peak,e); dd=(peak-e)/peak*100; mdd=max(mdd,dd)
print(f"Max DD: {mdd:.1f}%")
print(f"Reasons: {{'TP':{len([x for x in closed if x.get('reason')=='TP'])} 'SL':{len([x for x in closed if x.get('reason')=='SL'])} 'TRAIL':{len([x for x in closed if x.get('reason')=='TRAIL'])}}}")