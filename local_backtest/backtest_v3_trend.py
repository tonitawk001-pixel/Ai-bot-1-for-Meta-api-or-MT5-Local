"""V3 + EMA50 Trend Filter — Multi-Week Validation."""
import yfinance as yf, pandas as pd, numpy as np, warnings
warnings.filterwarnings("ignore")
from datetime import timedelta

BAL=1000.0; SP=0.20

def ema(s,p): return s.ewm(span=p,adjust=False).mean()
def rsi(s,p=14):
    d=s.diff();g=d.clip(lower=0).rolling(p).mean();l=-d.clip(upper=0).rolling(p).mean()
    return 100-100/(1+g/l.replace(0,np.nan))
def atr(h,l,c,p=14):
    tr=pd.concat([(h-l).abs(),(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()

print("Downloading M5 data...")
df=yf.download("GC=F",interval="5m",period="60d",progress=False)
if isinstance(df.columns,pd.MultiIndex):df.columns=[c[0] for c in df.columns]
df=df.rename(columns=str.lower).dropna(); df.index=pd.to_datetime(df.index,utc=True)
print(f"Total: {len(df)} candles")

df["rsi14"]=rsi(df["close"],14); df["atr"]=atr(df["high"],df["low"],df["close"],14); df["ema50"]=ema(df["close"],50)

def run_bt(df):
    bal=BAL; closed=[]; pos=[]; cons=0; halt=None; dpnl=0.0; ld=None; le=None
    for i in range(60,len(df)):
        ct=df.index[i];p=float(df["close"].iloc[i])
        if not(8<=ct.hour<22):continue
        d=ct.date()
        if ld is None:ld=d
        if d!=ld:dpnl=0.0;ld=d
        if halt and ct<halt:continue
        if dpnl<=-bal*0.10:continue
        av=float(df["atr"].iloc[i]); ema50=float(df["ema50"].iloc[i])
        if av<0.5:continue
        surv=[]
        for q in pos:
            e,d2,sl,tp,lot=q["entry"],q["dir"],q["sl"],q["tp"],q["lot"]
            pv=lot*100;hit=False;pnl=0;r=""
            if d2=="BUY":
                if tp and p>=tp:pnl=(tp-e)*pv;r="TP";hit=True
                elif sl and p<=sl:pnl=(sl-e)*pv;r="SL";hit=True
            else:
                if tp and p<=tp:pnl=(e-tp)*pv;r="TP";hit=True
                elif sl and p>=sl:pnl=(e-sl)*pv;r="SL";hit=True
            if hit:
                pnl-=SP*lot*100;dpnl+=pnl;q["pnl"]=pnl;q["reason"]=r;q["close_price"]=p;closed.append(q)
                if r=="SL":cons+=1
                else:cons=0
            else:surv.append(q)
        pos=surv
        for t in list(closed):
            if t.get("_p"):continue
            t["_p"]=True;bal+=t["pnl"]
        if cons>=5 and halt is None:halt=ct+timedelta(hours=4)
        if len(pos)>=1:continue
        if le and (ct-le).total_seconds()/60<1:continue
        rv=float(df["rsi14"].iloc[i]); trend_up=p>ema50
        dr="NONE";sc=0
        if rv<30 and trend_up:dr="BUY";sc=30-rv
        elif rv>70 and not trend_up:dr="SELL";sc=rv-70
        if dr=="NONE" or sc<5:continue
        sd=max(av*0.8,0.6);td=sd*2.5
        sl=round(p-sd,2) if dr=="BUY" else round(p+sd,2)
        tp=round(p+td,2) if dr=="BUY" else round(p-td,2)
        lot=max(0.01,min(round((bal*0.02)/(sd*100)/0.01)*0.01,10.0))
        pos.append({"entry":p,"sl":sl,"tp":tp,"lot":lot,"dir":dr,"open_time":ct}); le=ct
    if not closed:return None
    tp=0;wc=0;lc=0;wp=[];lp=[]
    for t in closed:
        pnl=t["pnl"];tp+=pnl
        if pnl>0:wc+=1;wp.append(pnl)
        else:lc+=1;lp.append(pnl)
    return {"pl":tp,"pct":tp/BAL*100,"trades":len(closed),"tpd":max(1,len(closed)//5),"win":wc,"loss":lc,"pf":abs(sum(wp)/sum(lp)) if wp and lp else 0}

end=df.index[-1]
weeks=[("Week A (Jul 9-16)",end-timedelta(days=7),end),("Week B (Jun 25-Jul 2)",end-timedelta(days=21),end-timedelta(days=14)),("Week C (Jun 4-11)",end-timedelta(days=42),end-timedelta(days=35))]
print("="*60);print("  V3 + EMA50 TREND FILTER");print("="*60)
results=[]
for name,s,e in weeks:
    sub=df[(df.index>=s)&(df.index<e)].copy()
    if len(sub)<100:continue
    r=run_bt(sub)
    if r:
        results.append(r)
        print(f"  {name}: P&L ${r['pl']:+.2f} ({r['pct']:+.1f}%)  {r['trades']} trades ({r['tpd']}/d)  PF {r['pf']:.2f}")
    else:
        print(f"  {name}: SKIPPED (no trades in range)")

if results:
    avg_pl=sum(r['pl'] for r in results)/len(results)
    avg_pf=sum(r['pf'] for r in results)/len(results)
    tot_trades=sum(r['trades'] for r in results)
    avg_day=sum(r['tpd'] for r in results)/len(results)
    print(f"\n  AVERAGE: P&L ${avg_pl:+.2f}  PF {avg_pf:.2f}  {tot_trades} trades ({avg_day:.0f}/day)")