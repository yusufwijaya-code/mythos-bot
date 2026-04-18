from datetime import datetime
from loguru import logger

from config.settings import settings
from app.core.database import SessionLocal
from app.core.risk_manager import RiskManager
from app.services.binance_client import BinanceService
from app.services.paper_trading import PaperTradingService
from app.services.pair_scanner import PairScanner
from app.strategies.ema_crossover import EMACrossoverStrategy
from app.strategies.multi_timeframe import MultiTimeframeStrategy
from app.strategies.base import SignalResult
from app.repositories.trade_repo import TradeRepository
from app.repositories.signal_repo import SignalRepository
from app.repositories.position_repo import PositionRepository


class TradingEngine:
    """Main orchestrator: strategy -> risk check -> execution -> notification."""

    def __init__(self, notifier=None):
        self.binance = BinanceService()
        self.paper = PaperTradingService()
        self.risk_manager = RiskManager()
        self.notifier = notifier
        self.active = False

        # Strategies
        self.strategies = {
            "ema_crossover": EMACrossoverStrategy(),
            "multi_timeframe": MultiTimeframeStrategy(),
        }
        self.active_strategy = "ema_crossover"

        # Pair scanner
        self.scanner = PairScanner(self.binance) if settings.SCANNER_ENABLED else None

        # Dedup tracking
        self._last_signals: dict[str, str] = {}  # pair -> last action

        # Uptime tracking
        self.start_time: datetime | None = None

        logger.info(
            f"Trading engine initialized | Mode: {settings.TRADING_MODE} | "
            f"Pairs: {settings.TRADING_PAIRS} | Strategy: {self.active_strategy}"
            + (f" | Scanner: ON (top {settings.SCANNER_TOP_PAIRS})" if self.scanner else "")
        )

    @property
    def is_paper(self) -> bool:
        return not settings.is_live

    def get_balance(self, asset: str = "USDT") -> float:
        if self.is_paper:
            return self.paper.get_balance(asset)
        return self.binance.get_balance(asset)

    def get_all_balances(self) -> dict:
        if self.is_paper:
            return self.paper.get_all_balances()
        return self.binance.get_all_balances()

    def get_initial_balance(self) -> float:
        if self.is_paper:
            return self.paper.initial_balance
        return 0  # For live, tracked differently

    def start(self):
        self.active = True
        self.start_time = datetime.utcnow()
        logger.info("Trading engine STARTED")

    def stop(self):
        self.active = False
        self.start_time = None
        logger.info("Trading engine STOPPED")

    def set_strategy(self, strategy_name: str):
        if strategy_name in self.strategies:
            self.active_strategy = strategy_name
            logger.info(f"Strategy changed to: {strategy_name}")

    def _get_trading_pairs(self) -> list[str]:
        """Get pairs to trade this cycle: open positions + scanner/config pairs."""
        pairs = set()

        # Always include pairs with open positions (must check SELL signals)
        db = SessionLocal()
        try:
            pos_repo = PositionRepository(db)
            for pos in pos_repo.get_open_positions(mode=settings.TRADING_MODE):
                pairs.add(pos.pair)
        finally:
            db.close()

        # Add pairs from scanner or static config
        if self.scanner:
            for p in self.scanner.get_top_pairs():
                pairs.add(p)
        else:
            for p in settings.TRADING_PAIRS:
                pairs.add(p)

        return list(pairs)

    def run_cycle(self):
        """Execute one trading cycle for all pairs."""
        if not self.active:
            return

        self.risk_manager.reset_daily()

        for pair in self._get_trading_pairs():
            try:
                self._process_pair(pair)
            except Exception as e:
                logger.error(f"Error processing {pair}: {e}")
                self.risk_manager.record_error()
                if self.notifier and self.risk_manager.is_emergency:
                    self.notifier.send_error(
                        f"EMERGENCY STOP - Too many errors. Last: {str(e)}"
                    )
                    self.stop()

    def _process_pair(self, pair: str):
        """Process a single trading pair."""
        # Check risk before anything
        balance = self.get_balance()
        initial = self.get_initial_balance()
        can_trade, reason = self.risk_manager.can_trade(balance, initial)

        if not can_trade:
            logger.warning(f"[{pair}] Trading blocked: {reason}")
            if self.risk_manager.is_emergency and self.notifier:
                self.notifier.send_error(f"Trading blocked: {reason}")
                self.stop()
            return

        # Get market data
        df = self.binance.get_klines(pair, settings.TIMEFRAME)
        if df.empty:
            logger.warning(f"[{pair}] No kline data received")
            return

        # Run strategy
        strategy = self.strategies[self.active_strategy]
        signal = strategy.analyze(df, pair)

        # Save signal to DB
        db = SessionLocal()
        try:
            signal_repo = SignalRepository(db)
            db_signal = signal_repo.create(
                pair=signal.pair,
                strategy=signal.strategy,
                action=signal.action,
                confidence=signal.confidence,
                indicators=signal.indicators,
            )

            if signal.action == "HOLD":
                return

            # Dedup: don't repeat the same signal consecutively
            last = self._last_signals.get(pair)
            if last == signal.action:
                logger.info(f"[{pair}] Duplicate {signal.action} signal, skipping")
                return

            # Check positions for SELL
            pos_repo = PositionRepository(db)
            trade_repo = TradeRepository(db)

            if signal.action == "SELL":
                self._handle_sell(pair, signal, pos_repo, trade_repo, db_signal.id, signal_repo)
            elif signal.action == "BUY":
                self._handle_buy(pair, signal, balance, pos_repo, trade_repo, db_signal.id, signal_repo)

        except Exception as e:
            logger.error(f"[{pair}] Processing error: {e}")
            self.risk_manager.record_error()
            db.rollback()
        finally:
            db.close()

    def _handle_buy(self, pair, signal, balance, pos_repo, trade_repo, signal_id, signal_repo):
        """Handle BUY signal execution."""
        # Check if already in position for this pair
        existing = pos_repo.get_open_position(pair, mode=settings.TRADING_MODE)
        if existing:
            logger.info(f"[{pair}] Already in position, skipping BUY")
            return

        # Check max concurrent open positions
        all_open = pos_repo.get_open_positions(mode=settings.TRADING_MODE)
        if len(all_open) >= settings.MAX_OPEN_POSITIONS:
            logger.info(
                f"[{pair}] Max positions ({settings.MAX_OPEN_POSITIONS}) reached, skipping BUY"
            )
            return

        price = self.binance.get_ticker_price(pair)
        if not price:
            return

        # Calculate position size
        step_size = self.binance.get_step_size(pair) if not self.is_paper else 0.00001
        quantity = self.risk_manager.calculate_position_size(balance, price, step_size)

        if quantity <= 0:
            logger.warning(f"[{pair}] Position size too small")
            return

        # Check minimum notional (quantity × price >= min_notional)
        if not self.is_paper:
            min_notional = self.binance.get_min_notional(pair)
            order_value = quantity * price
            if order_value < min_notional:
                logger.warning(
                    f"[{pair}] Order value {order_value:.2f} USDT below "
                    f"min notional {min_notional} USDT, skipping BUY"
                )
                return  # Not an error — just insufficient balance for this pair

        # Execute order
        if self.is_paper:
            order = self.paper.place_order(pair, "BUY", quantity, price)
        else:
            order = self.binance.place_order(pair, "BUY", quantity)

        if not order:
            self.risk_manager.record_error()
            return

        # Calculate SL/TP
        stop_loss = self.risk_manager.calculate_stop_loss(price)
        take_profit = self.risk_manager.calculate_take_profit(price)
        trailing_stop = self.risk_manager.calculate_trailing_stop(price, price, None)

        total = quantity * price

        # Save trade
        trade_repo.create(
            pair=pair,
            side="BUY",
            price=price,
            quantity=quantity,
            total=total,
            fee=total * 0.001,
            mode=settings.TRADING_MODE,
            order_id=order.get("orderId"),
            strategy=signal.strategy,
        )

        # Save position
        pos_repo.create(
            pair=pair,
            side="LONG",
            entry_price=price,
            quantity=quantity,
            current_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop=trailing_stop,
            mode=settings.TRADING_MODE,
        )

        signal_repo.mark_executed(signal_id)
        self._last_signals[pair] = "BUY"

        logger.info(
            f"[{pair}] BUY executed: {quantity} @ {price} | "
            f"SL: {stop_loss} | TP: {take_profit}"
        )

        if self.notifier:
            self.notifier.send_trade_buy(
                pair, price, stop_loss, take_profit,
                quantity=quantity, strategy=signal.strategy,
            )

    def _handle_sell(self, pair, signal, pos_repo, trade_repo, signal_id, signal_repo):
        """Handle SELL signal execution."""
        position = pos_repo.get_open_position(pair, mode=settings.TRADING_MODE)
        if not position:
            logger.info(f"[{pair}] No open position to sell")
            return

        price = self.binance.get_ticker_price(pair)
        if not price:
            return

        quantity = float(position.quantity)

        # For live trading, use actual free balance to account for trading fees
        # Binance deducts fee from received asset (e.g. BTC), so actual balance
        # is slightly less than the ordered quantity (e.g. 0.00013 * 0.999 = 0.00012987)
        if not self.is_paper:
            base_asset = pair.replace("USDT", "")
            actual_free = self.binance.get_free_balance(base_asset)
            if actual_free < quantity:
                step_size = self.binance.get_step_size(pair)
                if step_size > 0:
                    adjusted = int(actual_free / step_size) * step_size
                    adjusted = round(adjusted, 8)
                else:
                    adjusted = actual_free
                logger.info(
                    f"[{pair}] Adjusting SELL qty from {quantity} to {adjusted} "
                    f"(actual free: {actual_free})"
                )
                quantity = adjusted

            if quantity <= 0:
                logger.warning(f"[{pair}] No {base_asset} balance available to sell, skipping")
                return

            # Check minimum notional for SELL
            min_notional = self.binance.get_min_notional(pair)
            order_value = quantity * price
            if order_value < min_notional:
                is_forced = signal.strategy in ("stop_loss", "take_profit")
                if is_forced:
                    # SL/TP: value below NOTIONAL — try Binance Convert API first.
                    # Convert API bypasses NOTIONAL filter (designed for dust conversion).
                    base_asset = pair.replace("USDT", "")
                    entry_price = float(position.entry_price)
                    pnl = (price - entry_price) * quantity
                    pnl_pct = (price - entry_price) / entry_price * 100

                    convert_result = self.binance.convert_to_usdt(base_asset, quantity)
                    if convert_result:
                        reason = f"{signal.strategy.upper()} (auto-converted ke USDT)"
                        logger.info(
                            f"[{pair}] {signal.strategy.upper()} auto-converted "
                            f"{quantity} {base_asset} → USDT via Convert API"
                        )
                    else:
                        reason = (
                            f"{signal.strategy.upper()} — Posisi ditutup di sistem. "
                            f"⚠️ Jual {quantity} {base_asset} manual di Binance!"
                        )
                        logger.warning(
                            f"[{pair}] {signal.strategy.upper()} force-closed in DB "
                            f"(convert failed, {order_value:.4f} < min notional {min_notional} USDT). "
                            f"Sell {base_asset} manually!"
                        )

                    trade_repo.create(
                        pair=pair, side="SELL", price=price, quantity=quantity,
                        total=order_value, fee=0, pnl=pnl, pnl_pct=pnl_pct,
                        mode=settings.TRADING_MODE, strategy=signal.strategy,
                    )
                    pos_repo.close_position(position.id, current_price=price)
                    self.risk_manager.record_trade(pnl)
                    if signal_id:
                        signal_repo.mark_executed(signal_id)
                    self._last_signals[pair] = "SELL"
                    if self.notifier:
                        self.notifier.send_trade_sell(
                            pair, price, pnl_pct,
                            pnl=pnl, entry=entry_price, quantity=quantity,
                            reason=reason,
                        )
                else:
                    logger.warning(
                        f"[{pair}] SELL value {order_value:.4f} USDT below "
                        f"min notional {min_notional} USDT — holding, wait for price recovery"
                    )
                return

        # Execute order
        if self.is_paper:
            order = self.paper.place_order(pair, "SELL", quantity, price)
        else:
            order = self.binance.place_order(pair, "SELL", quantity)

        if not order:
            self.risk_manager.record_error()
            # Prevent retry loop: mark as last signal so dedup skips next cycle
            self._last_signals[pair] = "SELL"
            return

        entry_price = float(position.entry_price)
        total = quantity * price
        pnl = (price - entry_price) * quantity
        pnl_pct = (price - entry_price) / entry_price * 100

        # Save trade
        trade_repo.create(
            pair=pair,
            side="SELL",
            price=price,
            quantity=quantity,
            total=total,
            fee=total * 0.001,
            pnl=pnl,
            pnl_pct=pnl_pct,
            mode=settings.TRADING_MODE,
            order_id=order.get("orderId"),
            strategy=signal.strategy,
        )

        # Close position
        pos_repo.close_position(position.id, current_price=price)

        # Track in risk manager
        self.risk_manager.record_trade(pnl)

        signal_repo.mark_executed(signal_id)
        self._last_signals[pair] = "SELL"

        logger.info(
            f"[{pair}] SELL executed: {quantity} @ {price} | "
            f"PnL: {pnl:+.2f} ({pnl_pct:+.2f}%)"
        )

        if self.notifier:
            self.notifier.send_trade_sell(
                pair, price, pnl_pct,
                pnl=pnl, entry=entry_price, quantity=quantity,
                reason=signal.reason if hasattr(signal, "reason") else "",
            )

    def check_stop_loss_take_profit(self):
        """Check all open positions for SL/TP hits."""
        db = SessionLocal()
        try:
            pos_repo = PositionRepository(db)
            trade_repo = TradeRepository(db)
            signal_repo = SignalRepository(db)

            positions = pos_repo.get_open_positions(mode=settings.TRADING_MODE)

            for pos in positions:
                pair = pos.pair
                price = self.binance.get_ticker_price(pair)
                if not price:
                    continue

                entry = float(pos.entry_price)
                sl = float(pos.stop_loss) if pos.stop_loss else None
                tp = float(pos.take_profit) if pos.take_profit else None
                ts = float(pos.trailing_stop) if pos.trailing_stop else None

                # Update trailing stop
                new_ts = self.risk_manager.calculate_trailing_stop(
                    entry, price, ts, pos.side
                )
                pos_repo.update_price(pos.id, price, trailing_stop=new_ts)

                # Check SL
                if sl and self.risk_manager.should_stop_loss(entry, price, sl, new_ts, pos.side):
                    logger.warning(f"[{pair}] STOP LOSS triggered @ {price}")
                    sell_signal = SignalResult(
                        action="SELL", pair=pair, strategy="stop_loss",
                        reason="Stop loss triggered"
                    )
                    self._handle_sell(
                        pair, sell_signal, pos_repo, trade_repo, None, signal_repo
                    )
                    # Note: send_trade_sell() is already called inside _handle_sell()

                # Check TP
                elif tp and self.risk_manager.should_take_profit(price, tp, pos.side):
                    logger.info(f"[{pair}] TAKE PROFIT triggered @ {price}")
                    sell_signal = SignalResult(
                        action="SELL", pair=pair, strategy="take_profit",
                        reason="Take profit triggered"
                    )
                    self._handle_sell(
                        pair, sell_signal, pos_repo, trade_repo, None, signal_repo
                    )

        except Exception as e:
            logger.error(f"SL/TP check error: {e}")
        finally:
            db.close()
