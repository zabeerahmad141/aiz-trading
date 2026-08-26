from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel

from app.database import get_db
from app.models.trade import Trade, TradeAction, TradeStatus, Position
from app.models.user import User
from app.core.security import get_current_user, require_trader
from app.services.broker import get_active_broker
from app.config import settings

router = APIRouter()


class TradeRequest(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    stop_loss: float | None = None
    target_price: float | None = None


@router.get("/status")
async def bot_status(current_user: User = Depends(get_current_user)):
    broker = await get_active_broker()
    return {
        "is_running": True,
        "mode": settings.trading_mode,
        "broker": settings.active_broker,
        "market_open": await broker.is_market_open(),
        "balance": await broker.get_balance(),
        "capital": settings.trading_capital,
    }


@router.post("/order", dependencies=[Depends(require_trader)])
async def place_manual_order(
    payload: TradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    broker = await get_active_broker()
    if not await broker.is_market_open():
        raise HTTPException(status_code=400, detail="Market is closed")

    result = await broker.place_order(
        symbol=payload.symbol,
        action=payload.action.value,
        quantity=payload.quantity,
    )

    trade = Trade(
        user_id=current_user.id,
        symbol=payload.symbol,
        action=payload.action,
        quantity=payload.quantity,
        entry_price=result.price,
        stop_loss=payload.stop_loss,
        target_price=payload.target_price,
        status=TradeStatus.executed,
        broker_order_id=result.order_id,
        is_paper=result.is_paper,
        ai_signal="MANUAL",
        entered_at=datetime.utcnow(),
    )
    db.add(trade)
    await db.commit()
    return {"order_id": result.order_id, "price": result.price, "status": "executed"}


@router.get("/history")
async def trade_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(desc(Trade.entered_at))
        .limit(limit)
    )
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "action": t.action.value,
            "quantity": t.quantity,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "pnl": t.pnl,
            "status": t.status.value,
            "is_paper": t.is_paper,
            "ai_signal": t.ai_signal,
            "ai_confidence": t.ai_confidence,
            "entered_at": t.entered_at.isoformat(),
            "exited_at": t.exited_at.isoformat() if t.exited_at else None,
        }
        for t in trades
    ]


@router.get("/positions")
async def open_positions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Position).where(Position.user_id == current_user.id)
    )
    positions = result.scalars().all()
    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "quantity": p.quantity,
            "avg_price": p.avg_price,
            "current_price": p.current_price,
            "pnl": round(p.pnl, 2),
            "pnl_pct": round(p.pnl_pct, 2),
            "stop_loss": p.stop_loss,
            "target_price": p.target_price,
            "is_paper": p.is_paper,
            "opened_at": p.opened_at.isoformat(),
        }
        for p in positions
    ]
