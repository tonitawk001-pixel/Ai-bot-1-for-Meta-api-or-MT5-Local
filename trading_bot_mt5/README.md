# V22 Gold Bot — MT5 Local Edition

Runs directly on your **Windows laptop/PC** via MetaTrader5 Python library.  
No MetaApi, no cloud — direct connection to your broker through the MT5 terminal.

## Requirements
- **Windows** (required by MetaTrader 5 terminal)
- **MT5 terminal** installed and logged into your broker
- **Python 3.10+** installed

## Installation

### 1. Install Python
Download from: https://www.python.org/downloads/
- ✅ Check **"Add Python to PATH"** during installation
- ✅ Check **"Install pip"**

### 2. Install dependencies
Open **Command Prompt (cmd)** in this folder and run:
```cmd
pip install MetaTrader5 pandas numpy
```

### 3. Start MT5 terminal
- Open **MetaTrader 5** on your laptop
- Log in to your broker account
- Make sure **Auto Trading** is enabled (Tools → Options → Expert Advisors → ✅ Allow Automated Trading)

### 4. Run the bot
**Option A — Web Dashboard (recommended):**
Double-click `run_dashboard.bat` → opens http://localhost:5000
Click **START** → bot connects to MT5 and starts trading.

**Option B — Command line:**
```cmd
python main_mt5.py
```

### 5. Telegram Alerts (free)
Message `@Trading77777Bot` on Telegram to receive:
- 🟢 Bot started (with balance)
- 📈 Every trade opened (price, SL, TP, score)
- ✅ Trade closed (P&L, reason, new balance)
- 💚 Heartbeat every 5 minutes
- ⚠️ Error alerts

## Files
| File | Purpose |
|------|---------|
| `main_mt5.py` | Trading bot (EMA200 + RSI + ADX strategy) |
| `mt5_connection.py` | Direct MT5 terminal connection |
| `dashboard_simple.py` | Web dashboard with START/STOP/RESTART |
| `telegram_notifier.py` | Telegram trade alerts |
| `logger_mt5.py` | Standalone logger |
| `run_dashboard.bat` | Double-click to open dashboard |
| `test_mt5.py` | Quick connection test |
| `README.md` | This file |

## Strategy
- **EMA200** trend filter
- **RSI** confluence (M5 >40/M15 >40 for BUY, M5 <60/M15 <60 for SELL)
- **ADX** dynamic take profit (5x ATR when trending)
- **2% flat risk** per trade
- **Breakeven** at 2x ATR
- **Friday** entry block after 18:00 UTC, auto-close at 21:00 UTC
- **3-loss halt** with 6-hour cooldown
- **Daily loss limit** (3%)

## Dashboard
```
http://localhost:5000
```
- Shows live MT5 balance, equity, open positions, trades
- START/STOP/RESTART buttons
- Recent log viewer
- Auto-refresh every 5 seconds