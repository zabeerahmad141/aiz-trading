import secrets

from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from sqlalchemy import (
    select,
    desc,
)

from pydantic import BaseModel

from app.database import get_db

from app.models.trade import (
    Trade,
    TradeAction,
    TradeStatus,
    Position,
)

from app.models.user import User

from app.core.security import (
    get_current_user,
    require_trader,
)

from app.services.broker import (
    get_active_broker,
)

from app.config import settings


router = APIRouter()


# =============================================================
# Request models
# =============================================================


class TradeRequest(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    stop_loss: float | None = None
    target_price: float | None = None


class AITradeRequest(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int

    stop_loss: float | None = None

    target_price: float | None = None

    ai_signal: str | None = None

    ai_confidence: float | None = None

    ai_reason: str | None = None

    ltp: float | None = None


# =============================================================
# Helpers
# =============================================================


def _verify_internal_api_key(
    request: Request,
):
    """
    Authenticate internal ML Engine requests.

    ML Engine must send:

        X-Internal-Key: <configured secret>
    """

    configured_key = (
        settings.internal_api_key
    )

    if not configured_key:

        raise HTTPException(
            status_code=503,
            detail=(
                "Internal API key is not configured"
            ),
        )

    supplied_key = request.headers.get(
        "X-Internal-Key",
        "",
    )

    if not supplied_key:

        raise HTTPException(
            status_code=401,
            detail="Missing internal API key",
        )

    if not secrets.compare_digest(
        supplied_key,
        configured_key,
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid internal API key",
        )


async def _get_ai_trading_user(
    db: AsyncSession,
) -> User:
    """
    Get the configured system user responsible
    for automated AI trades.
    """

    result = await db.execute(
        select(User).where(
            User.id ==
            settings.ai_trading_user_id,

            User.is_active == True,
        )
    )

    user = result.scalar_one_or_none()

    if user is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Configured AI trading user "
                "does not exist or is inactive"
            ),
        )

    return user


async def _get_position(
    db: AsyncSession,
    user_id: int,
    symbol: str,
) -> Position | None:

    result = await db.execute(
        select(Position).where(
            Position.user_id == user_id,
            Position.symbol == symbol,
        )
    )

    return result.scalar_one_or_none()


async def _get_open_trade(
    db: AsyncSession,
    user_id: int,
    symbol: str,
) -> Trade | None:

    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id == user_id,
            Trade.symbol == symbol,
            Trade.action == TradeAction.buy,
            Trade.status == TradeStatus.executed,
            Trade.exit_price.is_(None),
        )
        .order_by(
            desc(Trade.entered_at)
        )
    )

    return result.scalars().first()


async def _create_or_update_position_after_buy(
    db: AsyncSession,
    user_id: int,
    symbol: str,
    quantity: int,
    price: float,
    stop_loss: float | None,
    target_price: float | None,
    is_paper: bool,
):
    """
    Create a new position after BUY.

    Duplicate positions are rejected before reaching here.
    """

    position = await _get_position(
        db,
        user_id,
        symbol,
    )

    if position is not None:

        raise HTTPException(
            status_code=409,
            detail=(
                f"Position already exists "
                f"for {symbol}"
            ),
        )

    position = Position(
        user_id=user_id,
        symbol=symbol,
        quantity=quantity,
        avg_price=price,
        current_price=price,
        stop_loss=stop_loss,
        target_price=target_price,
        is_paper=is_paper,
        opened_at=datetime.utcnow(),
    )

    db.add(position)

    return position


async def _close_position_after_sell(
    db: AsyncSession,
    user_id: int,
    symbol: str,
    price: float,
    quantity: int,
):
    """
    Close an existing position and calculate PnL.

    Returns:
        (position, pnl)
    """

    position = await _get_position(
        db,
        user_id,
        symbol,
    )

    if position is None:

        raise HTTPException(
            status_code=409,
            detail=(
                f"No open position for "
                f"{symbol}"
            ),
        )

    if quantity != position.quantity:

        raise HTTPException(
            status_code=400,
            detail=(
                "Partial SELL is not supported "
                "yet. "
                f"Existing quantity: "
                f"{position.quantity}, "
                f"requested: {quantity}"
            ),
        )

    pnl = (
        price -
        position.avg_price
    ) * position.quantity

    db.delete(position)

    return position, pnl


# =============================================================
# Status
# =============================================================


@router.get("/status")
async def bot_status(
    current_user: User = Depends(
        get_current_user
    ),
):
    broker = await get_active_broker()

    return {
        "is_running": True,
        "mode": settings.trading_mode,
        "broker": settings.active_broker,
        "market_open": (
            await broker.is_market_open()
        ),
        "balance": await broker.get_balance(),
        "capital": settings.trading_capital,
    }


# =============================================================
# Manual order
# =============================================================


@router.post(
    "/order",
    dependencies=[
        Depends(require_trader)
    ],
)
async def place_manual_order(
    payload: TradeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    symbol = payload.symbol.strip().upper()

    quantity = int(
        payload.quantity
    )

    if quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than zero",
        )

    broker = await get_active_broker()

    if not await broker.is_market_open():

        raise HTTPException(
            status_code=400,
            detail="Market is closed",
        )

    # ---------------------------------------------------------
    # BUY validation
    # ---------------------------------------------------------
    if payload.action == TradeAction.buy:

        existing = await _get_position(
            db,
            current_user.id,
            symbol,
        )

        if existing is not None:

            raise HTTPException(
                status_code=409,
                detail=(
                    f"Already have an open "
                    f"position in {symbol}"
                ),
            )

    # ---------------------------------------------------------
    # SELL validation
    # ---------------------------------------------------------
    if payload.action == TradeAction.sell:

        existing = await _get_position(
            db,
            current_user.id,
            symbol,
        )

        if existing is None:

            raise HTTPException(
                status_code=409,
                detail=(
                    f"No open position "
                    f"for {symbol}"
                ),
            )

        if quantity != existing.quantity:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Partial SELL is not "
                    "supported yet. "
                    f"Position quantity: "
                    f"{existing.quantity}"
                ),
            )

    # ---------------------------------------------------------
    # Execute broker order
    # ---------------------------------------------------------
    result = await broker.place_order(
        symbol=symbol,
        action=payload.action.value,
        quantity=quantity,
    )

    # ---------------------------------------------------------
    # BUY
    # ---------------------------------------------------------
    if payload.action == TradeAction.buy:

        trade = Trade(
            user_id=current_user.id,
            symbol=symbol,
            action=TradeAction.buy,
            quantity=quantity,
            entry_price=result.price,
            stop_loss=payload.stop_loss,
            target_price=payload.target_price,
            status=TradeStatus.executed,
            broker_order_id=result.order_id,
            is_paper=result.is_paper,
            ai_signal="MANUAL",
            ai_confidence=None,
            ai_reason="Manual trade",
            entered_at=datetime.utcnow(),
        )

        db.add(trade)

        await _create_or_update_position_after_buy(
            db=db,
            user_id=current_user.id,
            symbol=symbol,
            quantity=quantity,
            price=result.price,
            stop_loss=payload.stop_loss,
            target_price=payload.target_price,
            is_paper=result.is_paper,
        )

    # ---------------------------------------------------------
    # SELL
    # ---------------------------------------------------------
    else:

        position, pnl = (
            await _close_position_after_sell(
                db=db,
                user_id=current_user.id,
                symbol=symbol,
                price=result.price,
                quantity=quantity,
            )
        )

        open_trade = await _get_open_trade(
            db,
            current_user.id,
            symbol,
        )

        if open_trade is not None:

            open_trade.exit_price = (
                result.price
            )

            open_trade.pnl = pnl

            open_trade.exited_at = (
                datetime.utcnow()
            )

            open_trade.status = (
                TradeStatus.executed
            )

            open_trade.broker_order_id = (
                result.order_id
            )

        else:

            # Fallback in case a position exists
            # without a corresponding BUY trade.
            trade = Trade(
                user_id=current_user.id,
                symbol=symbol,
                action=TradeAction.sell,
                quantity=quantity,
                entry_price=position.avg_price,
                exit_price=result.price,
                pnl=pnl,
                status=TradeStatus.executed,
                broker_order_id=result.order_id,
                is_paper=result.is_paper,
                ai_signal="MANUAL",
                ai_reason="Manual trade",
                entered_at=(
                    position.opened_at
                ),
                exited_at=datetime.utcnow(),
            )

            db.add(trade)

    await db.commit()

    return {
        "order_id": result.order_id,
        "symbol": symbol,
        "action": payload.action.value,
        "quantity": quantity,
        "price": result.price,
        "status": "executed",
        "is_paper": result.is_paper,
    }


# =============================================================
# AI automated order
# =============================================================


@router.post("/ai-order")
async def place_ai_order(
    payload: AITradeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal ML Engine -> Backend execution endpoint.

    This endpoint is NOT intended for browser users.

    Authentication:
        X-Internal-Key

    Flow:

        ML Engine
            ↓
        Risk Manager
            ↓
        X-Internal-Key
            ↓
        Backend
            ↓
        Broker
            ↓
        Trade / Position DB
    """

    # ---------------------------------------------------------
    # 1. Authenticate ML Engine
    # ---------------------------------------------------------
    _verify_internal_api_key(
        request
    )

    # ---------------------------------------------------------
    # 2. Validate payload
    # ---------------------------------------------------------
    symbol = payload.symbol.strip().upper()

    quantity = int(
        payload.quantity
    )

    if not symbol:

        raise HTTPException(
            status_code=400,
            detail="Symbol is required",
        )

    if quantity <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Quantity must be greater "
                "than zero"
            ),
        )

    # ---------------------------------------------------------
    # 3. AI signal must match action
    # ---------------------------------------------------------
    if payload.ai_signal:

        ai_signal = (
            payload.ai_signal
            .strip()
            .upper()
        )

        if ai_signal not in (
            "BUY",
            "SELL",
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Invalid AI signal: "
                    f"{ai_signal}"
                ),
            )

        if (
            ai_signal.lower()
            != payload.action.value
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "AI signal and order "
                    "action do not match"
                ),
            )

    # ---------------------------------------------------------
    # 4. Get automated trading user
    # ---------------------------------------------------------
    current_user = (
        await _get_ai_trading_user(db)
    )

    # ---------------------------------------------------------
    # 5. Market status
    # ---------------------------------------------------------
    broker = await get_active_broker()

    if not await broker.is_market_open():

        raise HTTPException(
            status_code=400,
            detail="Market is closed",
        )

    # ---------------------------------------------------------
    # 6. BUY validation
    # ---------------------------------------------------------
    if payload.action == TradeAction.buy:

        existing = await _get_position(
            db,
            current_user.id,
            symbol,
        )

        if existing is not None:

            raise HTTPException(
                status_code=409,
                detail=(
                    f"AI BUY rejected. "
                    f"Already have position "
                    f"in {symbol}"
                ),
            )

    # ---------------------------------------------------------
    # 7. SELL validation
    # ---------------------------------------------------------
    if payload.action == TradeAction.sell:

        existing = await _get_position(
            db,
            current_user.id,
            symbol,
        )

        if existing is None:

            raise HTTPException(
                status_code=409,
                detail=(
                    f"AI SELL rejected. "
                    f"No open position "
                    f"for {symbol}"
                ),
            )

        if quantity != existing.quantity:

            raise HTTPException(
                status_code=400,
                detail=(
                    "AI partial SELL is "
                    "not supported yet. "
                    f"Position quantity: "
                    f"{existing.quantity}, "
                    f"requested: {quantity}"
                ),
            )

    # ---------------------------------------------------------
    # 8. Execute broker order
    # ---------------------------------------------------------
    result = await broker.place_order(
        symbol=symbol,
        action=payload.action.value,
        quantity=quantity,
    )

    # =========================================================
    # BUY
    # =========================================================
    if payload.action == TradeAction.buy:

        trade = Trade(
            user_id=current_user.id,
            symbol=symbol,
            action=TradeAction.buy,
            quantity=quantity,
            entry_price=result.price,
            stop_loss=payload.stop_loss,
            target_price=payload.target_price,
            status=TradeStatus.executed,
            broker_order_id=result.order_id,
            is_paper=result.is_paper,
            ai_signal=(
                payload.ai_signal
                or "BUY"
            ),
            ai_confidence=(
                payload.ai_confidence
            ),
            ai_reason=(
                payload.ai_reason
            ),
            entered_at=datetime.utcnow(),
        )

        db.add(trade)

        await _create_or_update_position_after_buy(
            db=db,
            user_id=current_user.id,
            symbol=symbol,
            quantity=quantity,
            price=result.price,
            stop_loss=payload.stop_loss,
            target_price=payload.target_price,
            is_paper=result.is_paper,
        )

        pnl = None

    # =========================================================
    # SELL
    # =========================================================
    else:

        position, pnl = (
            await _close_position_after_sell(
                db=db,
                user_id=current_user.id,
                symbol=symbol,
                price=result.price,
                quantity=quantity,
            )
        )

        open_trade = await _get_open_trade(
            db,
            current_user.id,
            symbol,
        )

        if open_trade is None:

            raise HTTPException(
                status_code=500,
                detail=(
                    "Position exists but "
                    "matching open BUY trade "
                    "was not found"
                ),
            )

        # Update original BUY trade
        # into a completed round trip.
        open_trade.exit_price = (
            result.price
        )

        open_trade.pnl = pnl

        open_trade.exited_at = (
            datetime.utcnow()
        )

        open_trade.broker_order_id = (
            result.order_id
        )

        # Preserve original AI BUY signal,
        # but update reason with exit information
        if payload.ai_reason:

            existing_reason = (
                open_trade.ai_reason
                or ""
            )

            open_trade.ai_reason = (
                f"{existing_reason} | "
                f"EXIT: {payload.ai_reason}"
            )

    # ---------------------------------------------------------
    # Commit DB changes
    # ---------------------------------------------------------
    await db.commit()

    logger_message = (
        f"AI TRADE EXECUTED | "
        f"{payload.action.value.upper()} "
        f"{quantity}x {symbol} | "
        f"₹{result.price:.2f} | "
        f"Order: {result.order_id}"
    )

    # Log without importing another logger dependency
    print(logger_message)

    return {
        "order_id": result.order_id,
        "symbol": symbol,
        "action": payload.action.value,
        "quantity": quantity,
        "price": result.price,
        "status": "executed",
        "is_paper": result.is_paper,
        "pnl": pnl,
        "ai_signal": payload.ai_signal,
        "ai_confidence": payload.ai_confidence,
    }


# =============================================================
# AI signals - display only
# =============================================================


@router.post("/ai-signals")
async def receive_ai_signals(
    payload: dict,
    request: Request,
):
    """
    Internal endpoint.

    Receives generated AI signals and broadcasts
    them to the frontend.

    IMPORTANT:
    This endpoint does NOT execute orders.
    Execution happens through /ai-order.
    """

    # Authenticate ML Engine
    _verify_internal_api_key(
        request
    )

    from app.routers.websocket import (
        broadcast_trade_event,
    )

    signals = payload.get(
        "signals",
        [],
    )

    if signals:

        await broadcast_trade_event(
            "ai_signals",
            {
                "signals": signals
            },
        )

    return {
        "received": len(signals)
    }


# =============================================================
# Trade history
# =============================================================


@router.get("/history")
async def trade_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):

    # Prevent abusive values
    limit = max(
        1,
        min(limit, 200),
    )

    result = await db.execute(
        select(Trade)
        .where(
            Trade.user_id ==
            current_user.id
        )
        .order_by(
            desc(Trade.entered_at)
        )
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
            "ai_confidence": (
                t.ai_confidence
            ),
            "ai_reason": t.ai_reason,
            "entered_at": (
                t.entered_at.isoformat()
            ),
            "exited_at": (
                t.exited_at.isoformat()
                if t.exited_at
                else None
            ),
        }
        for t in trades
    ]


# =============================================================
# Positions
# =============================================================


@router.get("/positions")
async def open_positions(
    current_user: User = Depends(
        get_current_user
    ),
    db: AsyncSession = Depends(
        get_db
    ),
):

    result = await db.execute(
        select(Position).where(
            Position.user_id ==
            current_user.id
        )
    )

    positions = (
        result.scalars().all()
    )

    return [
        {
            "id": p.id,
            "symbol": p.symbol,
            "quantity": p.quantity,
            "avg_price": p.avg_price,
            "current_price": (
                p.current_price
            ),
            "pnl": round(
                p.pnl,
                2,
            ),
            "pnl_pct": round(
                p.pnl_pct,
                2,
            ),
            "stop_loss": p.stop_loss,
            "target_price": (
                p.target_price
            ),
            "is_paper": p.is_paper,
            "opened_at": (
                p.opened_at.isoformat()
            ),
        }
        for p in positions
    ]
