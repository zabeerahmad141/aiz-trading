from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


class Candle(BaseModel):
    close: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    signal: str = "HOLD"


class BacktestRequest(BaseModel):
    candles: list[Candle] = Field(min_length=2, max_length=5000)
    initial_capital: float = Field(default=100000, gt=0)
    risk_per_trade_pct: float = Field(default=1, gt=0, le=10)
    stop_loss_pct: float = Field(default=1.5, gt=0, le=50)
    target_pct: float = Field(default=3, gt=0, le=100)
    commission_pct: float = Field(default=0.1, ge=0, le=10)


@router.post("/run")
async def run_backtest(payload: BacktestRequest, current_user: User = Depends(get_current_user)):
    cash = payload.initial_capital
    position = None
    completed = []
    equity_curve = [cash]

    for index, candle in enumerate(payload.candles):
        if candle.low > candle.high:
            raise HTTPException(status_code=422, detail=f"Candle {index} low exceeds high")
        if position:
            exit_price = None
            reason = None
            if candle.low <= position["stop_loss"]:
                exit_price, reason = position["stop_loss"], "stop_loss"
            elif candle.high >= position["target"]:
                exit_price, reason = position["target"], "target"
            elif candle.signal.upper() == "SELL":
                exit_price, reason = candle.close, "signal"
            if exit_price is not None:
                gross = (exit_price - position["entry_price"]) * position["quantity"]
                commission = (position["entry_price"] + exit_price) * position["quantity"] * payload.commission_pct / 100
                pnl = gross - commission
                cash += position["entry_price"] * position["quantity"] + pnl
                completed.append({**position, "exit_price": round(exit_price, 2), "reason": reason, "pnl": round(pnl, 2)})
                position = None

        if position is None and candle.signal.upper() == "BUY":
            risk_amount = cash * payload.risk_per_trade_pct / 100
            risk_per_share = candle.close * payload.stop_loss_pct / 100
            quantity = min(int(risk_amount / risk_per_share), int(cash / candle.close)) if risk_per_share else 0
            if quantity > 0:
                position = {"entry_index": index, "entry_price": candle.close, "quantity": quantity, "stop_loss": candle.close * (1 - payload.stop_loss_pct / 100), "target": candle.close * (1 + payload.target_pct / 100)}
                cash -= candle.close * quantity
        equity_curve.append(cash + (position["quantity"] * candle.close if position else 0))

    if position:
        final = payload.candles[-1].close
        pnl = (final - position["entry_price"]) * position["quantity"]
        cash += position["entry_price"] * position["quantity"] + pnl
        completed.append({**position, "exit_price": round(final, 2), "reason": "end_of_data", "pnl": round(pnl, 2)})

    peak = payload.initial_capital
    drawdown = 0.0
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak * 100)
    wins = sum(trade["pnl"] > 0 for trade in completed)
    total_pnl = sum(trade["pnl"] for trade in completed)
    return {
        "initial_capital": payload.initial_capital,
        "final_capital": round(cash, 2),
        "total_return_pct": round((cash / payload.initial_capital - 1) * 100, 2),
        "total_trades": len(completed),
        "winning_trades": wins,
        "losing_trades": sum(trade["pnl"] < 0 for trade in completed),
        "win_rate_pct": round(wins / len(completed) * 100, 2) if completed else 0,
        "max_drawdown_pct": round(drawdown, 2),
        "expectancy": round(total_pnl / len(completed), 2) if completed else 0,
        "trades": completed,
    }
