"""
MetaApi Execution Engine — trade placement via cloud API.

Drop-in replacement for `execution/mt5_executor.py`.

Same interface (execute_trade, close_position, modify_position) so the
rest of the bot code does not need to change.
"""

from typing import Optional
from datetime import datetime

from trading_bot.config import Config
from trading_bot.metaapi_connection import get_connection
from trading_bot.utils.logger import logger


def execute_trade(
    action: str,
    symbol: str,
    lot_size: float,
    sl: float,
    tp: float,
    ohlcv=None,
    risk_evaluation: Optional[dict] = None,
    account_list: Optional[list] = None,  # ignored — MetaApi uses one account
) -> list:
    """
    Place a single market order via MetaApi.

    Note: MetaApi uses a single account per bot (not multi-account
    like the original MT5 version).
    """
    if Config.EMERGENCY_STOP:
        logger.critical("EMERGENCY STOP ACTIVE — all execution blocked.")
        return [{"account": "METAAPI", "success": False, "reason": "Emergency stop active"}]

    if not Config.EXECUTION_ENABLED:
        logger.warning("EXECUTION_ENABLED is false. No trades placed.")
        return [{"account": "METAAPI", "success": False, "reason": "Execution disabled"}]

    if action.upper() not in ("BUY", "SELL"):
        return [{"account": "METAAPI", "success": False,
                 "reason": f"Invalid action {action}"}]

    if risk_evaluation and not risk_evaluation.get("approved", False):
        reason = risk_evaluation.get("reason", "Unknown")
        logger.warning(f"Risk engine BLOCKED trade: {reason}")
        return [{"account": "METAAPI", "success": False,
                 "reason": f"Risk block: {reason}"}]

    # Apply lot scaling from risk scoring
    adjusted_lot_scale = 1.0
    if risk_evaluation:
        adjusted_lot_scale = risk_evaluation.get("adjusted_lot_scale", 1.0)
    final_lot = round(lot_size * adjusted_lot_scale, 2)
    final_lot = max(Config.MIN_LOT_SIZE, min(final_lot, Config.MAX_LOT_SIZE))

    if adjusted_lot_scale < 1.0:
        logger.info(f"Risk scaling applied: {lot_size} * {adjusted_lot_scale} = {final_lot}")

    # Pre-execution checks (lot size)
    if final_lot < Config.MIN_LOT_SIZE or final_lot > Config.MAX_LOT_SIZE:
        return [{"account": "METAAPI", "success": False,
                 "reason": f"Lot {final_lot} out of range"}]

    try:
        conn = get_connection()
        result = conn.create_market_order(
            action=action,
            symbol=symbol,
            lot=final_lot,
            sl=round(sl, 2) if sl else 0.0,
            tp=round(tp, 2) if tp else 0.0,
            magic=202406,
            comment=f"V22_{action.upper()}",
        )
        result["account"] = "METAAPI"
        result["timestamp"] = datetime.now().isoformat()
        result["lot_size"] = final_lot
        return [result]
    except Exception as exc:
        logger.error(f"MetaApi execute_trade failed: {exc}")
        return [{"account": "METAAPI", "success": False,
                 "reason": f"Exception: {exc}"}]


def close_position(position_id: str, account: dict = None) -> dict:
    """Close a position by its MetaApi position id."""
    if Config.EMERGENCY_STOP:
        return {"success": False, "reason": "Emergency stop active"}
    try:
        conn = get_connection()
        return conn.close_position(position_id)
    except Exception as exc:
        return {"success": False, "reason": f"Exception: {exc}"}


def modify_position(position_id: str, sl: float = None, tp: float = None,
                    account: dict = None) -> dict:
    """Modify SL/TP of an open position."""
    if Config.EMERGENCY_STOP:
        return {"success": False, "reason": "Emergency stop active"}
    try:
        conn = get_connection()
        return conn.modify_position(position_id, sl=sl, tp=tp)
    except Exception as exc:
        return {"success": False, "reason": f"Exception: {exc}"}
