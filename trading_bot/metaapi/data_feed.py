"""
MetaApi Data Feed — candle fetcher.

Drop-in replacement for `mt5/data_feed.py`.
Returns pandas DataFrames with the same columns as the MT5 version.
"""

from typing import List, Optional

import pandas as pd

from trading_bot.metaapi_connection import get_connection
from trading_bot.utils.logger import logger


# Mapping from string timeframe labels to MetaApi SDK strings
TIMEFRAME_MAP = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
    "W1": "1w",
    "MN1": "1mn",
}


def get_candles(
    symbol: str,
    timeframe: str = "H1",
    count: int = 100,
) -> Optional[pd.DataFrame]:
    """
    Fetch the latest OHLCV candles via MetaApi Cloud.

    Returns a pandas DataFrame with the same schema as the MT5 version:
        - index: time (datetime)
        - columns: open, high, low, close, tick_volume, spread, real_volume
    """
    tf = TIMEFRAME_MAP.get(timeframe.upper())
    if tf is None:
        logger.error(
            f"Invalid timeframe '{timeframe}'. Valid: {list(TIMEFRAME_MAP.keys())}"
        )
        return None

    try:
        conn = get_connection()
        df = conn.get_candles_df(symbol=symbol, timeframe=timeframe, count=count)
        if df is None or df.empty:
            logger.warning(f"No candles returned for {symbol} ({timeframe})")
            return None
        logger.debug(f"Fetched {len(df)} candles for {symbol} ({timeframe})")
        return df
    except Exception as exc:
        logger.error(f"MetaApi fetch failed for {symbol} ({timeframe}): {exc}")
        return None


def get_candles_multiple_timeframes(
    symbol: str,
    timeframes: Optional[List[str]] = None,
    count: int = 100,
) -> dict:
    """Fetch candles for a symbol across multiple timeframes."""
    if timeframes is None:
        timeframes = ["M1", "M5", "M15"]

    result = {}
    for tf in timeframes:
        df = get_candles(symbol=symbol, timeframe=tf, count=count)
        if df is not None:
            result[tf] = df
    logger.info(f"Retrieved data for {symbol}: {list(result.keys())}")
    return result
