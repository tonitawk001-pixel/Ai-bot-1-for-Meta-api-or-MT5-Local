"""Quick test to verify MT5 connection on this machine."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import MetaTrader5 as mt5
    print("MetaTrader5 library: INSTALLED")
except ImportError:
    print("MetaTrader5 library: NOT INSTALLED")
    print("Run: pip install MetaTrader5")
    sys.exit(1)

print("Attempting to connect to MT5 terminal...")
if not mt5.initialize():
    error = mt5.last_error()
    print(f"FAILED: {error}")
    print("Make sure MT5 is OPEN and you are LOGGED IN")
    print("Also check: Tools > Options > Expert Advisors > Allow Automated Trading")
    sys.exit(1)

info = mt5.account_info()
if info:
    print("✅ MT5 CONNECTED SUCCESSFULLY")
    print(f"   Account: {info.login}")
    print(f"   Server:  {info.server}")
    print(f"   Balance: ${info.balance:.2f}")
    print(f"   Leverage: 1:{info.leverage}")
    print(f"   Trading Allowed: {info.trade_allowed}")
else:
    print("MT5 connected but no account logged in.")
    print("Please log into your broker in MT5 first.")

mt5.shutdown()