import time
from loguru import logger

from config.settings import settings


class PairScanner:
    """Scans Binance for top volume USDT pairs as trading candidates."""

    # Stablecoins and wrapped tokens to exclude
    EXCLUDED = {
        "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
        "USDPUSDT", "EURUSDT", "GBPUSDT", "AEURUSDT",
    }
    CACHE_DURATION = 900  # 15 minutes

    def __init__(self, binance_service):
        self.binance = binance_service
        self._cache: list[str] = []
        self._last_scan_time: float = 0

    def get_top_pairs(
        self,
        limit: int = None,
        min_volume: float = None,
    ) -> list[str]:
        """Get top USDT pairs sorted by 24h quote volume.

        Results are cached for 15 minutes to avoid API spam.
        """
        limit = limit or settings.SCANNER_TOP_PAIRS
        min_volume = min_volume or settings.SCANNER_MIN_VOLUME

        now = time.time()
        if self._cache and (now - self._last_scan_time) < self.CACHE_DURATION:
            return self._cache[:limit]

        try:
            tickers = self.binance.get_all_tickers()
            if not tickers:
                logger.warning("Scanner: no tickers returned from Binance")
                return self._cache[:limit] if self._cache else []

            usdt_pairs = []
            for t in tickers:
                symbol = t.get("symbol", "")
                if (
                    symbol.endswith("USDT")
                    and symbol not in self.EXCLUDED
                    and float(t.get("quoteVolume", 0)) >= min_volume
                ):
                    usdt_pairs.append({
                        "symbol": symbol,
                        "volume": float(t["quoteVolume"]),
                        "change": float(t.get("priceChangePercent", 0)),
                    })

            usdt_pairs.sort(key=lambda x: x["volume"], reverse=True)
            self._cache = [p["symbol"] for p in usdt_pairs[:limit]]
            self._last_scan_time = now

            logger.info(
                f"Scanner: refreshed top {len(self._cache)} pairs "
                f"(min vol: {min_volume/1e6:.0f}M USDT)"
            )
            return self._cache

        except Exception as e:
            logger.error(f"Scanner error: {e}")
            return self._cache[:limit] if self._cache else []

    def get_cached_pairs(self) -> list[str]:
        """Return currently cached pairs without refreshing."""
        return list(self._cache)
