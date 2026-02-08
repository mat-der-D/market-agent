from datetime import datetime, timezone

import yfinance


def fetch_usdjpy_rate() -> tuple[float, datetime]:
    """
    Fetch the current USD/JPY exchange rate from Yahoo Finance.

    Returns:
        A tuple of (rate, fetched_at) where rate is the USDJPY=X price
        and fetched_at is the UTC datetime of retrieval.

    Raises:
        RuntimeError: If the rate cannot be fetched.
    """
    ticker = yfinance.Ticker("USDJPY=X")
    rate = ticker.fast_info.last_price
    if rate is None or rate != rate:  # NaN check
        raise RuntimeError("為替レートの取得に失敗しました")
    fetched_at = datetime.now(tz=timezone.utc)
    return float(rate), fetched_at
