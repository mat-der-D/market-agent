from datetime import datetime, timezone

from rate_fetcher import fetch_usdjpy_rate


def convert(from_currency: str, to_currency: str, amount: float) -> dict:
    """
    Validate input, fetch rate, and perform currency conversion.

    Returns a dict with keys: result, rate, fetched_at
    or on error: {"error": "..."}
    """
    if amount < 0:
        return {"error": "Invalid amount"}

    if amount == 0:
        fetched_at = datetime.now(tz=timezone.utc)
        return {
            "result": 0.0,
            "rate": 0.0,
            "fetched_at": fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    try:
        rate, fetched_at = fetch_usdjpy_rate()
    except RuntimeError as exc:
        return {"error": str(exc)}

    if from_currency == "USD" and to_currency == "JPY":
        result = amount * rate
    elif from_currency == "JPY" and to_currency == "USD":
        result = amount / rate
    else:
        return {"error": f"Unsupported currency pair: {from_currency}/{to_currency}"}

    return {
        "result": round(result, 2),
        "rate": rate,
        "fetched_at": fetched_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
