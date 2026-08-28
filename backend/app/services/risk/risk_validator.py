"""Pre-trade risk and reward validation."""

from __future__ import annotations


class RiskValidator:
    """Reject trades with invalid levels or insufficient reward."""

    def __init__(self, minimum_risk_reward: float = 1.5):
        self.minimum_risk_reward = minimum_risk_reward

    def validate(self, entry: float, stop_loss: float, target: float, side: str = "BUY") -> dict:
        if entry <= 0 or stop_loss <= 0 or target <= 0:
            return {"valid": False, "risk_reward": 0.0, "reason": "Prices must be positive"}
        side = side.upper()
        if side == "BUY":
            levels_valid = stop_loss < entry < target
        elif side == "SELL":
            levels_valid = target < entry < stop_loss
        else:
            raise ValueError("side must be 'BUY' or 'SELL'")
        risk = abs(entry - stop_loss)
        reward = abs(target - entry)
        ratio = reward / risk if risk else 0.0
        valid = levels_valid and ratio >= self.minimum_risk_reward
        reason = "Risk/reward accepted" if valid else "Invalid levels or insufficient risk/reward"
        return {"valid": valid, "risk": round(risk, 4), "reward": round(reward, 4), "risk_reward": round(ratio, 4), "reason": reason}
