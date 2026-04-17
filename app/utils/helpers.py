from datetime import datetime, timezone


def timestamp_to_datetime(ts_ms: int) -> datetime:
    """Convert millisecond timestamp to datetime."""
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to millisecond timestamp."""
    return int(dt.timestamp() * 1000)


def format_price(price: float, decimals: int = 2) -> str:
    """Format price with proper decimal places."""
    return f"{price:,.{decimals}f}"


def format_pnl(pnl: float, pnl_pct: float | None = None) -> str:
    """Format PnL with sign and optional percentage."""
    sign = "+" if pnl >= 0 else ""
    result = f"{sign}{pnl:.2f}"
    if pnl_pct is not None:
        result += f" ({sign}{pnl_pct:.2f}%)"
    return result


def format_pair(pair: str) -> str:
    """Format pair for display (BTCUSDT -> BTC/USDT)."""
    if pair.endswith("USDT"):
        return f"{pair[:-4]}/USDT"
    if pair.endswith("BTC"):
        return f"{pair[:-3]}/BTC"
    return pair


def now_str() -> str:
    """Get current time as formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M")
