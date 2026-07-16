"""
MetaApi Cloud Connection Wrapper
=================================
High-reliability MetaTrader 5 access via MetaApi Cloud SDK.

The MetaApi Python SDK v29.x uses TypedDict for all response models,
so we access fields with dict syntax (obj["key"]) instead of attributes.

Works on Linux, macOS, Windows — no local MT5 terminal required.

Reads credentials from .env:
    METAAPI_TOKEN
    METAAPI_ACCOUNT_ID
    METAAPI_REGION (optional, default: new-york)
"""

import os
import asyncio
from typing import Optional

from metaapi_cloud_sdk import MetaApi
from metaapi_cloud_sdk.metaapi.models import GetPositionsOptions

from trading_bot.utils.logger import logger


# MetaApi SDK timeframe string mapping
TIMEFRAME_MAP = {
    "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
    "H1": "1h", "H4": "4h", "D1": "1d", "W1": "1w", "MN1": "1mn",
}


def _g(obj, key, default=None):
    """
    Get value from a dict OR an object (TypedDict compat).

    The MetaApi SDK returns TypedDict instances (which are dicts),
    so we use dict-style access. This helper makes the code work with
    both dicts and regular objects.
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class MetaApiConnection:
    """
    Synchronous wrapper around the MetaApi async SDK.
    """

    def __init__(self, region: Optional[str] = None):
        self.token = os.getenv("METAAPI_TOKEN", "").strip()
        self.account_id = os.getenv("METAAPI_ACCOUNT_ID", "").strip()
        self.region = region or os.getenv("METAAPI_REGION", "new-york").strip()

        if not self.token:
            raise ValueError("METAAPI_TOKEN is missing. Add it to your .env file.")
        if not self.account_id:
            raise ValueError("METAAPI_ACCOUNT_ID is missing. Add it to your .env file.")

        self.api: Optional[MetaApi] = None
        self.account = None
        self.connection = None
        self._initialized = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Event loop management
    # ------------------------------------------------------------------

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _run(self, coro):
        return self._get_loop().run_until_complete(coro)

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, timeout_in_seconds: int = 300) -> bool:
        if self._initialized:
            return True
        try:
            logger.info("Connecting to MetaApi cloud...")
            return self._run(self._async_initialize(timeout_in_seconds))
        except Exception as exc:
            logger.error(f"❌ MetaApi initialize failed: {exc}")
            return False

    async def _async_initialize(self, timeout_in_seconds: int) -> bool:
        self.api = MetaApi(self.token)

        account_api = self.api.metatrader_account_api
        self.account = await account_api.get_account(self.account_id)

        # Deploy if not already deployed
        try:
            if self.account.state not in ("DEPLOYED", "DEPLOYING"):
                logger.info("Deploying account (first-time setup)...")
                await self.account.deploy()
            else:
                logger.info(f"Account already in state: {self.account.state}")
        except Exception as deploy_err:
            logger.debug(f"Deploy call returned: {deploy_err}")

        # wait_deployed takes timeout_in_seconds
        logger.info("Waiting for broker connection...")
        await self.account.wait_deployed(
            timeout_in_seconds=timeout_in_seconds,
            interval_in_milliseconds=1000,
        )

        self.connection = self.account.get_rpc_connection()
        await self.connection.connect()
        await self.connection.wait_synchronized(timeout_in_seconds=60)

        # Verify with account info (TypedDict → use _g helper)
        info = await self.connection.get_account_information()
        balance = _g(info, "balance", 0.0)
        equity = _g(info, "equity", 0.0)
        leverage = _g(info, "leverage", 0)
        logger.info(
            f"✅ MetaApi connected | Balance: ${float(balance):.2f} | "
            f"Equity: ${float(equity):.2f} | Leverage: 1:{int(leverage)}"
        )
        self._initialized = True
        return True

    # ------------------------------------------------------------------
    # Account info
    # ------------------------------------------------------------------

    def get_account_info(self) -> dict:
        if not self._initialized:
            raise RuntimeError("MetaApiConnection not initialized")
        return self._run(self._async_get_account_info())

    async def _async_get_account_info(self) -> dict:
        info = await self.connection.get_account_information()
        return {
            "balance": float(_g(info, "balance", 0)),
            "equity": float(_g(info, "equity", 0)),
            "margin": float(_g(info, "margin", 0)),
            "free_margin": float(_g(info, "freeMargin", 0)),
            "margin_level": float(_g(info, "marginLevel", 0) or 0),
            "leverage": int(_g(info, "leverage", 0)),
            "currency": str(_g(info, "currency", "USD")),
            "name": str(_g(info, "name", "")),
            "login": int(_g(info, "login", 0)),
            "server": str(_g(info, "server", "")),
            "trade_allowed": bool(_g(info, "tradeAllowed", False)),
        }

    # ------------------------------------------------------------------
    # Symbols / Prices
    # ------------------------------------------------------------------

    def get_symbol_price(self, symbol: str) -> dict:
        return self._run(self._async_get_symbol_price(symbol))

    async def _async_get_symbol_price(self, symbol: str) -> dict:
        price = await self.connection.get_symbol_price(symbol)
        return {
            "symbol": symbol,
            "bid": float(_g(price, "bid", 0)),
            "ask": float(_g(price, "ask", 0)),
            "time": str(_g(price, "time", "")) if _g(price, "time") else None,
        }

    def get_symbol_specification(self, symbol: str) -> dict:
        return self._run(self._async_get_symbol_specification(symbol))

    async def _async_get_symbol_specification(self, symbol: str) -> dict:
        spec = await self.connection.get_symbol_specification(symbol)
        return {
            "symbol": symbol,
            "digits": int(_g(spec, "digits", 0)),
            "volume_min": float(_g(spec, "minVolume", 0)),
            "volume_max": float(_g(spec, "maxVolume", 0)),
            "volume_step": float(_g(spec, "volumeStep", 0)),
            "point": float(_g(spec, "point", 0)),
            "trade_mode": str(_g(spec, "tradeMode", "")),
        }

    # ------------------------------------------------------------------
    # Candles (uses account.get_historical_candles)
    # ------------------------------------------------------------------

    def get_candles_df(self, symbol: str, timeframe: str, count: int = 100):
        import pandas as pd

        tf = TIMEFRAME_MAP.get(timeframe.upper())
        if tf is None:
            raise ValueError(f"Invalid timeframe '{timeframe}'")

        candles = self._run(self._async_get_candles(symbol, tf, count))

        rows = []
        for c in candles:
            rows.append({
                "time": _g(c, "time"),
                "open": float(_g(c, "open", 0)),
                "high": float(_g(c, "high", 0)),
                "low": float(_g(c, "low", 0)),
                "close": float(_g(c, "close", 0)),
                "tick_volume": int(_g(c, "tickVolume", 0) or 0),
                "spread": int(_g(c, "spread", 0) or 0),
                "real_volume": int(_g(c, "realVolume", 0) or 0),
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df.sort_index(inplace=True)
        return df

    async def _async_get_candles(self, symbol: str, timeframe: str, count: int):
        limit = min(count, 1000)
        return await self.account.get_historical_candles(
            symbol=symbol,
            timeframe=timeframe,
            start_time=None,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Positions & Orders
    # ------------------------------------------------------------------

    def get_positions(self, symbol: Optional[str] = None) -> list:
        positions = self._run(self._async_get_positions(symbol))
        out = []
        for p in positions:
            out.append({
                "id": str(_g(p, "id", "")),
                "symbol": str(_g(p, "symbol", "")),
                "type": str(_g(p, "type", "")),
                "volume": float(_g(p, "volume", 0)),
                "open_price": float(_g(p, "openPrice", 0)),
                "sl": float(_g(p, "sl", 0) or 0),
                "tp": float(_g(p, "tp", 0) or 0),
                "profit": float(_g(p, "profit", 0) or 0),
                "magic": int(_g(p, "magic", 0) or 0),
            })
        return out

    async def _async_get_positions(self, symbol: Optional[str]):
        if symbol:
            opts = GetPositionsOptions(symbol=symbol)
            return await self.connection.get_positions(opts)
        return await self.connection.get_positions()

    def get_position(self, position_id: str) -> Optional[dict]:
        try:
            p = self._run(self.connection.get_position(position_id))
            if not p:
                return None
            return {
                "id": str(_g(p, "id", "")),
                "symbol": str(_g(p, "symbol", "")),
                "type": str(_g(p, "type", "")),
                "volume": float(_g(p, "volume", 0)),
                "open_price": float(_g(p, "openPrice", 0)),
                "sl": float(_g(p, "sl", 0) or 0),
                "tp": float(_g(p, "tp", 0) or 0),
                "profit": float(_g(p, "profit", 0) or 0),
            }
        except Exception:
            return None

    def close_position(self, position_id: str) -> dict:
        try:
            self._run(self.connection.close_position(position_id))
            return {"success": True, "reason": "Closed"}
        except Exception as exc:
            return {"success": False, "reason": f"Close failed: {exc}"}

    def modify_position(self, position_id: str, sl: float = None,
                        tp: float = None) -> dict:
        try:
            # modify_position uses stop_loss/take_profit kwargs
            self._run(self.connection.modify_position(
                position_id,
                stop_loss=sl or 0,
                take_profit=tp or 0,
            ))
            return {"success": True, "reason": "Modified"}
        except Exception as exc:
            return {"success": False, "reason": f"Modify failed: {exc}"}

    # ------------------------------------------------------------------
    # Order execution
    # ------------------------------------------------------------------

    def create_market_order(
        self,
        action: str,
        symbol: str,
        lot: float,
        sl: float = 0.0,
        tp: float = 0.0,
        magic: int = 202406,
        comment: str = "V22_METAAPI",
    ) -> dict:
        """
        Place a market order. action: "BUY" or "SELL".
        """
        try:
            if action.upper() == "BUY":
                result = self._run(self.connection.create_market_buy_order(
                    symbol=symbol,
                    volume=lot,
                    stop_loss=sl or 0,
                    take_profit=tp or 0,
                ))
            elif action.upper() == "SELL":
                result = self._run(self.connection.create_market_sell_order(
                    symbol=symbol,
                    volume=lot,
                    stop_loss=sl or 0,
                    take_profit=tp or 0,
                ))
            else:
                return {"success": False, "reason": f"Invalid action '{action}'"}

            order_id = str(_g(result, "orderId", _g(result, "positionId", "")))
            return {
                "success": True,
                "reason": "Executed",
                "order_id": order_id,
                "string_code": str(_g(result, "stringCode", "")),
                "numeric_code": int(_g(result, "numericCode", 0)),
            }
        except Exception as exc:
            return {"success": False, "reason": f"Order failed: {exc}"}

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        try:
            if self.connection:
                try:
                    self._run(self.connection.close())
                except Exception:
                    pass
                logger.info("MetaApi RPC connection closed.")
        except Exception:
            pass
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.close()
            except Exception:
                pass
        self._loop = None
        self._initialized = False


# ----------------------------------------------------------------------
# Singleton helper
# ----------------------------------------------------------------------

_singleton: Optional[MetaApiConnection] = None


def get_connection() -> MetaApiConnection:
    global _singleton
    if _singleton is None or not _singleton._initialized:
        _singleton = MetaApiConnection()
        _singleton.initialize()
    return _singleton
