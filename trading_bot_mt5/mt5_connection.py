"""
MT5 Local Connection Module
============================
Replaces metaapi_connection.py for direct local MetaTrader 5 access.
Requires MT5 terminal to be running and logged into your broker.
"""

import os
import pandas as pd
from datetime import datetime, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 library not installed. Run: pip install MetaTrader5")
    mt5 = None

from logger_mt5 import logger

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Connection:
    """Synchronous wrapper around MetaTrader5 terminal."""

    def __init__(self):
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize connection to the MT5 terminal."""
        if mt5 is None:
            logger.critical("MetaTrader5 library not available")
            return False

        if self._initialized:
            return True

        logger.info("Connecting to local MT5 terminal...")
        if not mt5.initialize():
            error = mt5.last_error()
            logger.critical(f"MT5 initialize failed: {error}")
            return False

        # Verify terminal is connected to a broker
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            logger.critical("Cannot get terminal info. Make sure MT5 is running.")
            mt5.shutdown()
            return False

        account_info = mt5.account_info()
        if account_info is None:
            logger.warning("MT5 connected but no account logged in. Please log in via MT5 terminal.")
            return False

        login = account_info.login
        balance = account_info.balance
        server = account_info.server
        logger.info(f"✅ MT5 connected | Account: {login} | Server: {server} | Balance: ${balance:.2f}")
        self._initialized = True
        return True

    def shutdown(self):
        """Shutdown MT5 connection."""
        if self._initialized and mt5:
            mt5.shutdown()
            self._initialized = False
            logger.info("MT5 connection closed.")

    def get_account_info(self) -> dict:
        """Get current account information."""
        if not self._initialized or mt5 is None:
            return None
        info = mt5.account_info()
        if info is None:
            return None
        return {
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "margin_level": info.margin_level,
            "leverage": info.leverage,
            "currency": info.currency,
            "name": info.name,
            "login": info.login,
            "server": info.server,
            "trade_allowed": info.trade_allowed,
        }

    def get_candles(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        """Fetch candles from MT5 terminal."""
        tf = TIMEFRAME_MAP.get(timeframe.upper())
        if tf is None:
            logger.error(f"Invalid timeframe '{timeframe}'")
            return None

        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, min(count, 1000))
            if rates is None or len(rates) == 0:
                return None

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)
            df.sort_index(inplace=True)
            df.rename(columns={
                "open": "open", "high": "high", "low": "low", "close": "close",
                "tick_volume": "tick_volume", "spread": "spread", "real_volume": "real_volume",
            }, inplace=True)
            return df
        except Exception as e:
            logger.warning(f"Failed to fetch {timeframe} candles: {e}")
            return None

    def get_symbol_price(self, symbol: str) -> dict:
        """Get current bid/ask for a symbol."""
        if not self._initialized or mt5 is None:
            return None
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return {"symbol": symbol, "bid": tick.bid, "ask": tick.ask}

    def get_symbol_specification(self, symbol: str) -> dict:
        """Get symbol specification (min/max volume, step, etc)."""
        if not self._initialized or mt5 is None:
            return {"volume_min": 0.01, "volume_max": 10.0, "volume_step": 0.01}
        info = mt5.symbol_info(symbol)
        if info is None:
            return {"volume_min": 0.01, "volume_max": 10.0, "volume_step": 0.01}
        return {
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
            "digits": info.digits,
            "point": info.point,
            "trade_mode": info.trade_mode,
        }

    def get_positions(self, symbol: str = None) -> list:
        """Get open positions."""
        if not self._initialized or mt5 is None:
            return []
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        if positions is None:
            return []
        result = []
        for p in positions:
            result.append({
                "id": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "open_price": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "magic": p.magic,
            })
        return result

    def close_position(self, position_id: int) -> dict:
        """Close a position by ticket number."""
        if not self._initialized or mt5 is None:
            return {"success": False, "reason": "Not initialized"}
        try:
            position = mt5.positions_get(ticket=position_id)
            if position is None or len(position) == 0:
                return {"success": False, "reason": f"Position {position_id} not found"}

            pos = position[0]
            symbol = pos.symbol
            lot = pos.volume
            price = mt5.symbol_info_tick(symbol).bid if pos.type == 0 else mt5.symbol_info_tick(symbol).ask
            order_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "position": position_id,
                "price": price,
                "deviation": 10,
                "magic": 202406,
                "comment": "V22_CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"success": True, "reason": "Closed"}
            else:
                error = result.comment if result else "No result"
                return {"success": False, "reason": f"Close failed: {error}"}
        except Exception as e:
            return {"success": False, "reason": f"Exception: {e}"}

    def modify_position(self, position_id: int, sl: float = None, tp: float = None) -> dict:
        """Modify SL/TP of an open position."""
        if not self._initialized or mt5 is None:
            return {"success": False, "reason": "Not initialized"}
        try:
            position = mt5.positions_get(ticket=position_id)
            if position is None or len(position) == 0:
                return {"success": False, "reason": f"Position {position_id} not found"}

            pos = position[0]
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": pos.symbol,
                "position": position_id,
                "sl": sl if sl is not None else pos.sl,
                "tp": tp if tp is not None else pos.tp,
                "magic": 202406,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"success": True, "reason": "Modified"}
            else:
                error = result.comment if result else "No result"
                return {"success": False, "reason": f"Modify failed: {error}"}
        except Exception as e:
            return {"success": False, "reason": f"Exception: {e}"}

    def place_order(self, action: str, symbol: str, lot: float, sl: float = 0.0, tp: float = 0.0) -> dict:
        """Place a market order."""
        if not self._initialized or mt5 is None:
            return {"success": False, "reason": "Not initialized"}

        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "reason": f"Cannot get price for {symbol}"}

        if action.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif action.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            return {"success": False, "reason": f"Invalid action {action}"}

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": order_type,
            "price": price,
            "sl": sl if sl else 0.0,
            "tp": tp if tp else 0.0,
            "deviation": 10,
            "magic": 202406,
            "comment": "V22_MT5",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        try:
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return {
                    "success": True,
                    "reason": "Executed",
                    "order_id": result.order,
                    "price": result.price,
                }
            else:
                error = result.comment if result else "No result"
                return {"success": False, "reason": f"Order failed: {error}"}
        except Exception as e:
            return {"success": False, "reason": f"Exception: {e}"}