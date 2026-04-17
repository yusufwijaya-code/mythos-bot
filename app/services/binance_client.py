from typing import Optional
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger

from config.settings import settings


class BinanceService:
    """Wrapper around Binance API for market data and order execution."""

    TIMEFRAME_MAP = {
        "1m": Client.KLINE_INTERVAL_1MINUTE,
        "5m": Client.KLINE_INTERVAL_5MINUTE,
        "15m": Client.KLINE_INTERVAL_15MINUTE,
        "1h": Client.KLINE_INTERVAL_1HOUR,
        "4h": Client.KLINE_INTERVAL_4HOUR,
        "1d": Client.KLINE_INTERVAL_1DAY,
    }

    def __init__(self):
        self.client = Client(
            settings.BINANCE_API_KEY,
            settings.BINANCE_API_SECRET,
        )
        logger.info("Binance client initialized")

    def get_klines(
        self, pair: str, timeframe: str = "1h", limit: int = 200
    ) -> pd.DataFrame:
        """Fetch OHLCV kline data from Binance."""
        try:
            interval = self.TIMEFRAME_MAP.get(timeframe, Client.KLINE_INTERVAL_1HOUR)
            klines = self.client.get_klines(
                symbol=pair, interval=interval, limit=limit
            )

            df = pd.DataFrame(
                klines,
                columns=[
                    "timestamp", "open", "high", "low", "close", "volume",
                    "close_time", "quote_volume", "trades", "taker_buy_base",
                    "taker_buy_quote", "ignore",
                ],
            )

            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)

            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            return df

        except BinanceAPIException as e:
            logger.error(f"Binance API error fetching klines for {pair}: {e}")
            return pd.DataFrame()

    def get_ticker_price(self, pair: str) -> Optional[float]:
        """Get current price for a pair."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=pair)
            return float(ticker["price"])
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting ticker for {pair}: {e}")
            return None

    def get_balance(self, asset: str = "USDT") -> float:
        """Get free + locked balance for an asset."""
        try:
            balance = self.client.get_asset_balance(asset=asset)
            if balance:
                return float(balance["free"]) + float(balance["locked"])
            return 0.0
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting balance for {asset}: {e}")
            return 0.0

    def get_total_portfolio_usdt(self) -> float:
        """Get total portfolio value in USDT (all assets converted to USDT equivalent).

        Handles Binance Simple Earn tokens (LD-prefixed, e.g. LDUSDT, LDBTC)
        by stripping the LD prefix to get the underlying asset price.
        """
        STABLECOINS = {"USDT", "BUSD", "USDC", "TUSD", "USDP", "DAI", "FDUSD"}
        try:
            account = self.client.get_account()
            total = 0.0
            for b in account["balances"]:
                asset = b["asset"]
                amount = float(b["free"]) + float(b["locked"])
                if amount <= 0:
                    continue

                # Binance Simple Earn tokens are LD-prefixed (e.g. LDUSDT, LDBTC)
                # Strip the prefix to get the underlying asset
                underlying = asset[2:] if asset.startswith("LD") else asset

                if underlying in STABLECOINS:
                    total += amount  # 1:1 USDT equivalent
                    continue

                # Convert to USDT via live market price
                pair = f"{underlying}USDT"
                try:
                    price = self.get_ticker_price(pair)
                    if price and price > 0:
                        total += amount * price
                except Exception:
                    pass  # Skip assets with no USDT pair
            return round(total, 2)
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting portfolio value: {e}")
            return self.get_balance("USDT")

    def get_all_balances(self) -> dict:
        """Get all non-zero balances."""
        try:
            account = self.client.get_account()
            balances = {}
            for b in account["balances"]:
                free = float(b["free"])
                locked = float(b["locked"])
                if free > 0 or locked > 0:
                    balances[b["asset"]] = {"free": free, "locked": locked}
            return balances
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting balances: {e}")
            return {}

    def place_order(
        self,
        pair: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
    ) -> Optional[dict]:
        """Place an order on Binance.

        Args:
            pair: Trading pair (e.g., BTCUSDT)
            side: "BUY" or "SELL"
            quantity: Order quantity
            order_type: "MARKET" or "LIMIT"

        Returns:
            Order response dict or None if failed
        """
        try:
            if order_type == "MARKET":
                order = self.client.create_order(
                    symbol=pair,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                )
            else:
                logger.warning(f"Order type {order_type} not yet supported")
                return None

            logger.info(
                f"Order placed: {side} {quantity} {pair} @ MARKET | "
                f"Order ID: {order['orderId']}"
            )
            return order

        except BinanceAPIException as e:
            logger.error(f"Binance order error: {side} {quantity} {pair} - {e}")
            return None

    def get_symbol_info(self, pair: str) -> Optional[dict]:
        """Get symbol trading rules (lot size, min qty, etc)."""
        try:
            info = self.client.get_symbol_info(pair)
            return info
        except Exception as e:
            logger.error(f"Error getting symbol info for {pair}: {e}")
            return None

    def get_min_quantity(self, pair: str) -> float:
        """Get minimum order quantity for a pair."""
        info = self.get_symbol_info(pair)
        if info:
            for f in info.get("filters", []):
                if f["filterType"] == "LOT_SIZE":
                    return float(f["minQty"])
        return 0.0

    def get_step_size(self, pair: str) -> float:
        """Get step size for order quantity."""
        info = self.get_symbol_info(pair)
        if info:
            for f in info.get("filters", []):
                if f["filterType"] == "LOT_SIZE":
                    return float(f["stepSize"])
        return 0.001
