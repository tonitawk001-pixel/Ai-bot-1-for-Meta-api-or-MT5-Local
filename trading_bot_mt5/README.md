# V22 Gold Scalping Bot — Local MT5 Edition

Runs directly on your **Windows laptop** via the MetaTrader5 Python library. No MetaApi, no cloud — direct connection to your broker.

## Requirements
- **Windows** (required by MetaTrader 5 terminal)
- **MT5 terminal** installed and logged into your broker
- **Python 3.10+** installed

## Installation

### 1. Install Python
Download from: https://www.python.org/downloads/
- ✅ Check "Add Python to PATH" during installation
- ✅ Check "Install pip"

### 2. Install dependencies
Open **Command Prompt (cmd)** and run:
```cmd
cd trading_bot_mt5
pip install MetaTrader5 pandas numpy python-dotenv
```

### 3. Download the bot files
Either:
- Clone the repo: `git clone https://github.com/tonitawk001-pixel/Ai-bot-fast-scalper-MT5.git`
- Or download the `trading_bot_mt5` folder manually

### 4. Start MT5 terminal
- Open **MetaTrader 5** on your laptop
- Log in to your broker account
- Make sure **"Auto Trading"** is enabled (Tools → Options → Expert Advisors → ✅ Allow Automated Trading)

### 5. Run the bot
```cmd
cd trading_bot_mt5
python main_mt5.py
```

## How it works
- The bot connects to your **local MT5 terminal**
- Fetches M5 and M15 candles directly from the terminal
- Applies the same strategy (EMA200 + RSI + ADX) as the cloud version
- Places trades directly through your MT5 terminal
- **No MetaApi needed** — no WebSocket disconnections

## Keeping it running
- The bot runs in a terminal window
- Keep it open while you want to trade
- Close it with **Ctrl+C**
- For 24/7 operation, consider getting a Windows VPS

## Troubleshooting
| Problem | Solution |
|---------|---------|
| `ModuleNotFoundError: No module named 'MetaTrader5'` | Run `pip install MetaTrader5` |
| `MT5 initialize failed` | Make sure MT5 terminal is running and logged in |
| `Order failed: Market is closed` | Normal outside trading hours (08:00-22:00 UTC) |
| Can't see XAUUSD in Market Watch | Press Ctrl+U in MT5, right-click → Symbols → Show XAUUSD |