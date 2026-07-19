"""Check if today's BUY signal would have been a winner or loser."""
import yfinance as yf
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

def fix_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns=str.lower)
    return df

# Signal details from the simulation
entry_price = 4074.50
sl = 4067.38
tp = 4091.11
signal_time_utc = "2026-07-15 18:15"
be_target = 4084.00  # approximate (entry + atr*2)

# Download M1 data after the signal to see what happened
print("=" * 70)
print("  TRADE OUTCOME ANALYSIS")
print(f"  Signal: BUY at ${entry_price} (18:15 UTC)")
print(f"  SL: ${sl} | TP: ${tp} | Breakeven: ~${be_target}")
print("=" * 70)

# Get detailed M1 data for the hours after the signal
df = yf.download("GC=F", interval="5m", start="2026-07-15", end="2026-07-16", progress=False)
if df is not None and not df.empty:
    df = fix_columns(df).dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    
    # Filter data from signal time onwards
    signal_dt = pd.Timestamp(signal_time_utc).tz_localize('UTC')
    after_signal = df[df.index >= signal_dt].copy()
    
    if len(after_signal) > 0:
        print(f"\nPrice movement after signal:")
        print(f"  {after_signal.index[0].strftime('%H:%M UTC')}: ${after_signal['close'].iloc[0]:.2f}")
        
        # Track what happened
        max_price = after_signal['close'].iloc[0]
        min_price = after_signal['close'].iloc[0]
        hit_tp = False
        hit_sl = False
        hit_be = False
        tp_time = None
        sl_time = None
        
        for idx, row in after_signal.iterrows():
            price = float(row['close'])
            max_price = max(max_price, price)
            min_price = min(min_price, price)
            
            if price >= tp and not hit_tp:
                hit_tp = True
                tp_time = idx
            if price <= sl and not hit_sl:
                hit_sl = True
                sl_time = idx
            if price >= be_target and not hit_be:
                hit_be = True
        
        print(f"  Max reached: ${max_price:.2f}")
        print(f"  Min reached: ${min_price:.2f}")
        print(f"  Last price:  ${after_signal['close'].iloc[-1]:.2f}")
        print(f"\n  TP hit ({tp})? {'✅ YES at ' + tp_time.strftime('%H:%M UTC') if tp_time else '❌ NO'}")
        print(f"  SL hit ({sl})? {'✅ YES at ' + sl_time.strftime('%H:%M UTC') if sl_time else '❌ NO'}")
        print(f"  Breakeven reached? {'✅ YES' if hit_be else '❌ NO'}")
        
        if hit_tp:
            profit = (tp - entry_price) * 0.01 * 100
            print(f"\n  🏆 WINNING TRADE: +${profit:.2f}")
        elif hit_sl:
            loss = (sl - entry_price) * 0.01 * 100
            print(f"\n  💀 LOSING TRADE: ${loss:.2f}")
        else:
            current_price = after_signal['close'].iloc[-1]
            if current_price > entry_price:
                profit = (current_price - entry_price) * 0.01 * 100
                print(f"\n  ⏳ STILL OPEN (floating +${profit:.2f})")
            else:
                loss = (current_price - entry_price) * 0.01 * 100
                print(f"\n  ⏳ STILL OPEN (floating ${loss:.2f})")
    else:
        print("No data after signal time")
else:
    print("Could not download data")

print("\n" + "=" * 70)