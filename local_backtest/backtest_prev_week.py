"""Test previous week (Jun 30-Jul 7) with exact V22 bot logic."""
import os,sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from datetime import timedelta
from trading_bot.indicators.technical_indicators import compute_all_indicators
from trading_bot.strategy.gold_scalping_strategy import GoldScalpingStrategy
BAL=304.99;SP=0.50

d5=yf.download("GC=F",interval="5m",period="60d",progress=False)
d15=yf.download("GC=F",interval="15m",period="60d",progress=False)
for d in[d5,d15]:
 if isinstance(d.columns,pd.MultiIndex):d.columns=[c[0] for c in d.columns]
d5=d5.rename(columns=str.lower).dropna();d5.index=pd.to_datetime(d5.index,utc=True)
d15=d15.rename(columns=str.lower).dropna();d15.index=pd.to_datetime(d15.index,utc=True)

end=d15.index[-1]-timedelta(days=14)
d15w=d15[(d15.index>=end)&(d15.index<end+timedelta(days=7))].copy()
d5w=d5[(d5.index>=end)&(d5.index<end+timedelta(days=7))].copy()

sg=GoldScalpingStrategy();sg._max_trades_per_day=50
bal=BAL;closed=[];pos=[];cons=0;halt=None;dpnl=0.0;ld=None;le=None;lm=None

for i in range(200,len(d15w)):
 ct=d15w.index[i];p=float(d15w["close"].iloc[i])
 if not(8<=ct.hour<22):continue
 d=ct.date()
 if ld is None:ld=d
 if d!=ld:dpnl=0.0;ld=d
 if halt and ct<halt:continue
 if dpnl<=-bal*0.03:continue
 if lm is not None and ct<=lm:continue
 m15w=d15w.iloc[max(0,i-499):i+1].copy()
 m5u=d5w[d5w.index<=ct];m5w=m5u.tail(500).copy()
 if len(m15w)<50 or len(m5w)<50:continue
 m5i=compute_all_indicators(m5w);m15i=compute_all_indicators(m15w)
 if m5i is None or m15i is None:continue
 if m5i.get("atr") is None or len(m5i["atr"])==0:continue
 atrv=float(m5i["atr"].iloc[-1])
 if atrv<1.0:lm=ct;continue
 surv=[]
 for q in pos:
  e,d2,sl,tp,lot=q["entry"],q["dir"],q["sl"],q["tp"],q["lot"];pv=lot*100
  if not q.get("be",False) and q.get("be_target"):
   if d2=="BUY" and p>=q["be_target"]:q["be"]=True;q["sl"]=e
   elif d2=="SELL" and p<=q["be_target"]:q["be"]=True;q["sl"]=e
  if q.get("be"):
   ns=p-atrv*0.7 if d2=="BUY" else p+atrv*0.7
   if d2=="BUY" and ns>sl+0.5:q["sl"]=round(ns,2)
   elif d2=="SELL" and ns<sl-0.5:q["sl"]=round(ns,2)
  sl,tp2=q["sl"],q["tp"]
  hit=False;pnl=0;r=""
  if d2=="BUY":
   if tp2 and p>=tp2:pnl=(tp2-e)*pv;r="TP";hit=True
   elif sl and p<=sl:pnl=(sl-e)*pv;r="SL";hit=True
  else:
   if tp2 and p<=tp2:pnl=(e-tp2)*pv;r="TP";hit=True
   elif sl and p>=sl:pnl=(e-sl)*pv;r="SL";hit=True
  if hit:
   pnl-=SP*lot*100;dpnl+=pnl;q["pnl"]=pnl;q["reason"]=r;closed.append(q)
   if r=="SL" and pnl<0:cons+=1
   else:cons=0
  else:surv.append(q)
 pos=surv
 for t in list(closed):
  if t.get("_p"):continue
  t["_p"]=True;bal+=t["pnl"]
 if cons>=3 and halt is None:halt=ct+timedelta(hours=6);cons=0
 if len(pos)>=1:lm=ct;continue
 if le and (ct-le).total_seconds()/60<30:lm=ct;continue
 em1={"rsi":pd.Series([50]),"emas":pd.DataFrame(),"macd":pd.Series([0])}
 try:r2=sg.analyze(m1_indicators=em1,m5_indicators=m5i,m15_indicators=m15i,m1_ohlcv=m5w.tail(20),m5_ohlcv=m5w,m15_ohlcv=m15w,news_context=None)
 except:lm=ct;continue
 direction=r2.get("direction","NONE");score=r2.get("setup_score",0)
 if direction=="NONE" or score<45:lm=ct;continue
 try:
  if direction=="BUY" and not(m5i["rsi"].iloc[-1]>40 and m15i["rsi"].iloc[-1]>40):lm=ct;continue
  if direction=="SELL" and not(m5i["rsi"].iloc[-1]<60 and m15i["rsi"].iloc[-1]<60):lm=ct;continue
 except:pass
 cs=m15w["close"].values
 if len(cs)>=200:
  e200=pd.Series(cs).ewm(200,adjust=False).mean().values
  if len(e200)>=10:
   rising=e200[-1]>e200[-10]
   if direction=="BUY" and not rising:lm=ct;continue
   if direction=="SELL" and rising:lm=ct;continue
 sd=atrv*1.5;td=atrv*3.5
 sl=round(p-sd,2) if direction=="BUY" else round(p+sd,2)
 tp2=round(p+td,2) if direction=="BUY" else round(p-td,2)
 lot=max(0.01,min(round((bal*0.02)/(sd*100)/0.01)*0.01,10.0))
 bt=p+(atrv*2.0 if direction=="BUY" else -atrv*2.0)
 pos.append({"entry":p,"sl":sl,"tp":tp2,"lot":lot,"dir":direction,"open_time":ct,"score":score,"be_target":bt,"be":False})
 le=ct;lm=ct
tt=0;wc=0;lc=0;wp=[];lp=[];dt={}
for t in closed:
 pnl=t["pnl"];tt+=pnl
 if pnl>0:wc+=1;wp.append(pnl)
 else:lc+=1;lp.append(pnl)
 dk=t["open_time"].date();dt[dk]=dt.get(dk,0)+1
print("SAFE BOT - PREV WEEK (Jun 30-Jul 7) [REAL M5/M15]")
print(f"P&L: ${tt:+.2f}  Trades: {len(closed)}  Win: {wc}({wc/len(closed)*100:.0f}%) Loss: {lc}")
if wp and lp:print(f"PF: {abs(sum(wp)/sum(lp)):.2f} AvgW: ${(sum(wp)/len(wp)):.2f} AvgL: ${(sum(lp)/len(lp)):.2f}")
for d in sorted(dt):
 dp=sum(t["pnl"] for t in closed if t["open_time"].date()==d)
 print(f"  {str(d)[5:]:<8} {dt[d]:>2} tr ${dp:+.2f}")
if not closed:print("  No trades")