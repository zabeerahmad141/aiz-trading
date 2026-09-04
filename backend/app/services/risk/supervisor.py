"""Database-backed protective-exit supervisor."""

from __future__ import annotations

import asyncio
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.trade import OrderIntent, Position, Trade, TradeAction, TradeStatus
from app.services.broker import get_active_broker
from app.services.market_data import get_active_market_data
from app.services.risk.exit_manager import ExitManager


class ExitSupervisor:
    """Evaluate and execute protective exits independently of browser/ML polling."""

    def __init__(self, interval_seconds: int = 15):
        self.interval_seconds = max(5, interval_seconds)
        self.manager = ExitManager()
        self._symbol_locks: dict[str, asyncio.Lock] = {}

    async def run(self):
        while True:
            try:
                await self.check_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Protective exit supervisor failed: {}", exc)
            await asyncio.sleep(self.interval_seconds)

    async def check_once(self):
        async with AsyncSessionLocal() as db:
            positions = (await db.execute(select(Position))).scalars().all()
            if not positions:
                return

            market_data = await get_active_market_data()
            broker = await get_active_broker()
            for position in positions:
                lock = self._symbol_locks.setdefault(position.symbol, asyncio.Lock())
                async with lock:
                    await self._check_position(db, position, market_data, broker)

    async def _check_position(self, db, position, market_data, broker):
        try:
            quote = await asyncio.wait_for(market_data.get_quote(position.symbol), timeout=8)
            if quote.ltp <= 0:
                return
            position.current_price = quote.ltp
            decision = self.manager.evaluate(
                side="BUY",
                entry_price=position.avg_price,
                current_price=quote.ltp,
                stop_loss=position.stop_loss or position.avg_price * (1 - settings.stop_loss_pct / 100),
                target=position.target_price or position.avg_price * (1 + settings.target_pct / 100),
                now=datetime.now(),
            )
            if not decision.should_exit:
                await db.commit()
                return

            key = f"exit:{position.id}:{decision.reason}"
            existing = await db.scalar(select(OrderIntent).where(OrderIntent.idempotency_key == key))
            if existing:
                return
            db.add(OrderIntent(
                idempotency_key=key,
                user_id=position.user_id,
                symbol=position.symbol,
                action=TradeAction.sell,
                quantity=position.quantity,
                status="pending",
            ))
            await db.flush()

            result = await broker.place_order(position.symbol, "sell", position.quantity, price=quote.ltp)
            intent = await db.scalar(select(OrderIntent).where(OrderIntent.idempotency_key == key))
            intent.status = "executed"
            intent.broker_order_id = result.order_id
            trade = await db.scalar(select(Trade).where(
                Trade.user_id == position.user_id,
                Trade.symbol == position.symbol,
                Trade.action == TradeAction.buy,
                Trade.status == TradeStatus.executed,
                Trade.exit_price.is_(None),
            ).order_by(Trade.entered_at.desc()))
            if trade:
                trade.exit_price = result.price
                trade.pnl = (result.price - trade.entry_price) * trade.quantity
                trade.exited_at = datetime.utcnow()
                trade.broker_order_id = result.order_id
            db.delete(position)
            await db.commit()
            logger.info("Protective exit executed: {} {} @ {}", decision.reason, position.symbol, result.price)
        except Exception as exc:
            await db.rollback()
            logger.warning("Protective exit unavailable for {}: {}", position.symbol, exc)
