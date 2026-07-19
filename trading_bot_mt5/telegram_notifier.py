"""
Telegram Notifier Module
========================
Sends notifications to your Telegram bot about trades, errors, and heartbeat.

Setup:
1. Open Telegram, search @Trading77777Bot, send any message
2. The bot auto-detects your Chat ID
"""

import requests
import time
from datetime import datetime, timezone

# === CONFIGURE THESE ===
TOKEN = "8576199875:AAHYRdna3TxQwHP50cpd9isW128BzBuvFKM"
CHAT_ID = 5233262246  # Your Telegram Chat ID (ToniTawk)

# Account name for multi-account support
ACCOUNT_NAME = "Default"

_last_heartbeat_time = 0
_HEARTBEAT_INTERVAL = 300  # 5 minutes

def send_message(text: str):
    """Send a text message to Telegram."""
    if not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
        return True
    except Exception as e:
        print(f"[Telegram] Send failed: {e}")
        return False

def set_chat_id(new_id: int):
    """Set the chat ID (auto-detected from Telegram)."""
    global CHAT_ID
    CHAT_ID = new_id

def set_account_name(name: str):
    """Set the account name for multi-account messages."""
    global ACCOUNT_NAME
    ACCOUNT_NAME = name

def try_auto_detect_chat_id():
    """Try to auto-detect chat ID from Telegram updates."""
    global CHAT_ID
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
        r = requests.get(url, timeout=10).json()
        if r.get("result"):
            for update in r["result"]:
                if "message" in update and "chat" in update["message"]:
                    cid = update["message"]["chat"]["id"]
                    CHAT_ID = cid
                    # Save to a file for persistence
                    with open("telegram_chat_id.txt", "w") as f:
                        f.write(str(cid))
                    send_message(f"🤖 Account: {ACCOUNT_NAME}\n✅ Bot connected! You will receive trade alerts here.")
                    return True
    except:
        pass
    # Try to load from saved file
    try:
        with open("telegram_chat_id.txt") as f:
            CHAT_ID = int(f.read().strip())
            return True
    except:
        pass
    return False

def notify_startup(balance=None):
    """Send bot startup notification with optional balance."""
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"🟢 <b>BOT STARTED</b>\n"
    )
    if balance is not None:
        msg += f"💰 <b>Balance:</b> ${balance:.2f}\n"
    msg += f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    send_message(msg)

def notify_shutdown():
    """Send bot shutdown notification."""
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"🔴 <b>BOT STOPPED</b>\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )
    send_message(msg)

def notify_trade_opened(direction: str, symbol: str, price: float, lot: float, sl: float, tp: float, score: int, balance: float):
    """Send notification when a trade is opened."""
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"📈 <b>TRADE OPENED</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>Direction:</b> {direction}\n"
        f"<b>Symbol:</b> {symbol}\n"
        f"<b>Price:</b> ${price:.2f}\n"
        f"<b>Lot:</b> {lot}\n"
        f"<b>SL:</b> ${sl:.2f}\n"
        f"<b>TP:</b> ${tp:.2f}\n"
        f"<b>Score:</b> {score}\n"
        f"<b>Balance:</b> ${balance:.2f}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
    )
    send_message(msg)

def notify_trade_closed(direction: str, symbol: str, entry: float, exit_price: float, pnl: float, reason: str, balance: float):
    """Send notification when a trade is closed."""
    emoji = "✅" if pnl > 0 else "❌"
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"{emoji} <b>TRADE CLOSED</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>Direction:</b> {direction}\n"
        f"<b>Symbol:</b> {symbol}\n"
        f"<b>Entry:</b> ${entry:.2f}\n"
        f"<b>Exit:</b> ${exit_price:.2f}\n"
        f"<b>P&L:</b> ${pnl:+.2f}\n"
        f"<b>Reason:</b> {reason}\n"
        f"<b>Balance:</b> ${balance:.2f}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
    )
    send_message(msg)

def notify_error(error_msg: str):
    """Send error notification."""
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"⚠️ <b>ERROR</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{error_msg[:200]}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
    )
    send_message(msg)

def notify_heartbeat(balance: float, open_positions: int, total_trades: int):
    """Send heartbeat every 5 minutes."""
    global _last_heartbeat_time
    now = time.time()
    if now - _last_heartbeat_time < _HEARTBEAT_INTERVAL:
        return
    _last_heartbeat_time = now
    
    msg = (
        f"🤖 <b>ACCOUNT: {ACCOUNT_NAME}</b>\n"
        f"💚 <b>BOT ALIVE</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>Balance:</b> ${balance:.2f}\n"
        f"<b>Open Positions:</b> {open_positions}\n"
        f"<b>Total Trades:</b> {total_trades}\n"
        f"⏰ {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC"
    )
    send_message(msg)