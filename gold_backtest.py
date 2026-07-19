import yfinance as yf
import pandas as pd
import numpy as np

print("[1/3] Downloading 12 months of historical Gold data from Yahoo Finance...")
df = yf.download("GC=F", period="1y", interval="1d")

# Flat column headers in case of MultiIndex
if isinstance(df.columns, pd.MultiIndex):
    df.columns = [col[0] for col in df.columns]

# Fallback in case GC=F is not responsive
if df.empty:
    print("Warning: 'GC=F' empty. Trying 'GLD'...")
    df = yf.download("GLD", period="1y", interval="1d")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

if df.empty:
    print("Error: Could not retrieve Gold data. Check connection.")
    exit()

df = df.dropna()

# Technical Indicators (EMA 50 for Trend Filtering)
df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

# Simulation Parameters
INITIAL_BALANCE = 300.0
LEVERAGE = 500
CONTRACT_SIZE = 100    # Standard Gold contract size (100 oz per 1.0 lot)
BASE_GRID_STEP = 15.0  # $15 move in gold price before next level
LOT_MULTIPLIER = 1.4   # Safer lot scaling multiplier
BASE_LOT = 0.01
TAKE_PROFIT_USD = 15.0 # Target profit to close out a grid cycle
HARD_STOP_LOSS_PCT = 0.35 # Maximum allowable drawdown (35% of starting capital)

balance = INITIAL_BALANCE
equity = INITIAL_BALANCE
max_drawdown_pct = 0.0
total_cycles = 0
hard_stops_hit = 0
open_positions = []
margin_called = False

print("[2/3] Simulating Safeguarded Grid/Martingale strategy...")

for date, row in df.iterrows():
    date_str = str(date.date()) if hasattr(date, 'date') else str(date)
    current_price = float(row['Close'])
    ema = float(row['EMA_50'])
    
    if pd.isna(ema):
        continue  # Wait for EMA indicator to warm up
        
    # Calculate Floating PnL and Margin
    floating_pnl = 0.0
    used_margin = 0.0
    for pos in open_positions:
        direction = 1.0 if pos['type'] == 'BUY' else -1.0
        pnl = (current_price - pos['entry_price']) * CONTRACT_SIZE * pos['lots'] * direction
        floating_pnl += pnl
        used_margin += (pos['entry_price'] * CONTRACT_SIZE * pos['lots']) / LEVERAGE
        
    equity = balance + floating_pnl
    
    # Calculate Drawdown
    drawdown_pct = 0.0
    if balance > 0:
        drawdown_pct = ((balance - equity) / balance) * 100
    if drawdown_pct > max_drawdown_pct:
        max_drawdown_pct = drawdown_pct
        
    # Check Stop Out / Margin Call (MT5 Stop Out level typical at 50% Margin Level)
    if len(open_positions) > 0 and used_margin > 0:
        margin_level = (equity / used_margin) * 100
        if margin_level < 50 or equity <= 0:
            print(f" -> !!! MARGIN CALL on {date_str} at gold price ${current_price:.2f} !!!")
            balance = 0.0
            equity = 0.0
            open_positions = []
            margin_called = True
            break
            
    # Check Hard Stop Loss Protection (Protects the account from complete ruin)
    if len(open_positions) > 0 and (balance - equity) >= (INITIAL_BALANCE * HARD_STOP_LOSS_PCT):
        loss_taken = balance - equity
        balance = equity
        print(f" -> [Risk Control] Hard Stop Loss triggered on {date_str} at price ${current_price:.2f}. Closed all trades. Loss: ${loss_taken:.2f}")
        open_positions = []
        hard_stops_hit += 1
        continue
        
    # Check Take Profit
    if len(open_positions) > 0 and floating_pnl >= TAKE_PROFIT_USD:
        balance += floating_pnl
        equity = balance
        open_positions = []
        total_cycles += 1
        continue
        
    # Grid Entry Decisions
    if len(open_positions) == 0:
        # Trend filter: Buy only above EMA, Sell only below EMA
        trade_type = 'BUY' if current_price > ema else 'SELL'
        open_positions.append({
            'type': trade_type,
            'entry_price': current_price,
            'lots': BASE_LOT
        })
    else:
        grid_type = open_positions[0]['type']
        last_pos = open_positions[-1]
        num_levels = len(open_positions)
        
        # Grid Stretching: steps get wider the deeper the drawdown goes
        dynamic_step = BASE_GRID_STEP * (1.15 ** (num_levels - 1))
        
        if grid_type == 'BUY':
            if current_price <= (last_pos['entry_price'] - dynamic_step):
                new_lots = round(last_pos['lots'] * LOT_MULTIPLIER, 2)
                if new_lots <= last_pos['lots']:
                    new_lots = round(last_pos['lots'] + 0.01, 2)
                open_positions.append({
                    'type': 'BUY',
                    'entry_price': current_price,
                    'lots': new_lots
                })
        elif grid_type == 'SELL':
            if current_price >= (last_pos['entry_price'] + dynamic_step):
                new_lots = round(last_pos['lots'] * LOT_MULTIPLIER, 2)
                if new_lots <= last_pos['lots']:
                    new_lots = round(last_pos['lots'] + 0.01, 2)
                open_positions.append({
                    'type': 'SELL',
                    'entry_price': current_price,
                    'lots': new_lots
                })

print("\n==========================================")
print("     GOLD BACKTEST RESULTS (SAFEGUARDED)")
print("==========================================")
print(f"Initial Balance:        ${INITIAL_BALANCE:.2f}")
print(f"Ending Balance:         ${balance:.2f}")
print(f"Ending Equity:          ${equity:.2f}")
print(f"Max Drawdown:           {max_drawdown_pct:.2f}%")
print(f"Total Cycles completed: {total_cycles}")
print(f"Hard Stops hit:         {hard_stops_hit}")
if margin_called:
    print("Status:                 Wiped Out (Margin Call)")
else:
    print("Status:                 Active & Protected")
print("==========================================\n")
