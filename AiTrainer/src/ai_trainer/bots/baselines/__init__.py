"""Deterministic baseline bots used to validate the runtime."""

from ai_trainer.bots.baselines.buy_and_hold import BuyAndHoldBot
from ai_trainer.bots.baselines.moving_average import MovingAverageBot
from ai_trainer.bots.baselines.random_bot import RandomBot

__all__ = ["BuyAndHoldBot", "MovingAverageBot", "RandomBot"]
