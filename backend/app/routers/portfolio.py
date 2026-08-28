from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.trade import Trade, TradeStatus, TradeAction
from app.models.user import User
from app.core.security import get_current_user
from app.services.broker import get_active_broker
from app.config import settings

router = APIRouter()


@router.get("/summary")
async def portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    broker = await get_active_broker()
    balance = await broker.get_balance()

    # Stats from DB
    result = await db.execute(
        select(
            func.count(Trade.id).label("total_trades"),
            func.sum(Trade.pnl).label("total_pnl"),
            func.count(Trade.id).filter(Trade.pnl > 0).label("wins"),
        ).where(Trade.user_id == current_user.id, Trade.status == TradeStatus.executed)
    )
    stats = result.one()
    total = stats.total_trades or 0
    wins = stats.wins or 0
    total_pnl = float(stats.total_pnl or 0)
    win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

    return {
        "portfolio_value": round(balance + total_pnl, 2),
        "available_balance": round(balance, 2),
        "total_pnl": round(total_pnl, 2),
        "total_trades": total,
        "win_rate": win_rate,
        "wins": wins,
        "losses": total - wins,
        "capital": settings.trading_capital,
        "broker": settings.active_broker,
        "mode": settings.trading_mode,
    }


@router.get("/pnl-chart")
async def pnl_chart(
    period: str = "today",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns cumulative P&L data points for charting."""
    from datetime import datetime, timedelta
    since = {
        "today": datetime.utcnow().replace(hour=0, minute=0, second=0),
        "week": datetime.utcnow() - timedelta(days=7),
        "month": datetime.utcnow() - timedelta(days=30),
    }.get(period, datetime.utcnow().replace(hour=0))

    result = await db.execute(
        select(Trade.entered_at, Trade.pnl)
        .where(Trade.user_id == current_user.id, Trade.entered_at >= since, Trade.pnl.isnot(None))
        .order_by(Trade.entered_at)
    )
    trades = result.all()

    cumulative = 0.0
    points = []
    for t in trades:
        cumulative += float(t.pnl or 0)
        points.append({"time": t.entered_at.isoformat(), "value": round(cumulative, 2)})

    return {"period": period, "data": points}


@router.get("/sessions")
async def portfolio_sessions(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent completed trading sessions for off-hours review."""
    limit = max(1, min(limit, 30))
    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == current_user.id,
            Trade.status == TradeStatus.executed,
        )
        .order_by(desc(Trade.entered_at))
        .limit(200),
    )
    grouped: dict[str, dict] = {}
    for trade in result.scalars():
        session_date = trade.entered_at.date().isoformat()
        session = grouped.setdefault(
            session_date,
            {"date": session_date, "trades": 0, "wins": 0, "losses": 0, "pnl": 0.0},
        )
        session["trades"] += 1
        pnl = float(trade.pnl or 0)
        session["pnl"] += pnl
        if pnl > 0:
            session["wins"] += 1
        elif pnl < 0:
            session["losses"] += 1

    sessions = list(grouped.values())[:limit]
    for session in sessions:
        session["pnl"] = round(session["pnl"], 2)
        session["win_rate"] = round(session["wins"] / session["trades"] * 100, 1)
    return {"sessions": sessions}
