"""Compact technical features from completed candles only."""

import math
from collections.abc import Sequence

from shared.contracts import Candle

VERSION = "market_features_v1"


def market_features(candles: Sequence[Candle], index: int) -> dict[str, float | None]:
    """Features at a candle close. ``candles[index]`` must be complete at decision time."""
    closes = [float(x.close) for x in candles[: index + 1]]
    volumes = [float(x.volume) for x in candles[: index + 1]]
    current = candles[index]

    def change(periods: int) -> float | None:
        return closes[-1] / closes[-1 - periods] - 1 if len(closes) > periods else None

    def ema(period: int) -> float | None:
        if len(closes) < period:
            return None
        alpha = 2 / (period + 1)
        value = sum(closes[:period]) / period
        for price in closes[period:]:
            value = alpha * price + (1 - alpha) * value
        return value

    fast, slow = ema(6), ema(12)
    signal_values: list[float] = []
    if len(closes) >= 12:
        for stop in range(11, len(closes)):
            f = _ema(closes[: stop + 1], 6)
            s = _ema(closes[: stop + 1], 12)
            if f is not None and s is not None:
                signal_values.append(f - s)
    macd = fast - slow if fast is not None and slow is not None else None
    signal = _ema(signal_values, 5)
    returns = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    rolling_returns = returns[-12:]
    volume_window = volumes[-12:]
    volume_mean = sum(volume_window) / len(volume_window)
    volume_std = _std(volume_window)
    return {
        "market_return_1": change(1),
        "market_return_3": change(3),
        "market_return_6": change(6),
        "market_return_12": change(12),
        "market_log_return": math.log(closes[-1] / closes[-2]) if len(closes) > 1 else None,
        "market_volume": volumes[-1],
        "market_volume_change": volumes[-1] / volumes[-2] - 1
        if len(volumes) > 1 and volumes[-2]
        else None,
        "market_rolling_volume_mean": volume_mean,
        "market_volume_zscore": (volumes[-1] - volume_mean) / volume_std if volume_std else None,
        "market_high_low_range": float((current.high - current.low) / current.open),
        "market_ema_fast": fast,
        "market_ema_slow": slow,
        "market_ema_distance": (fast / slow - 1) if fast is not None and slow else None,
        "market_rsi": _rsi(closes, 14),
        "market_macd": macd,
        "market_macd_signal": signal,
        "market_macd_histogram": macd - signal if macd is not None and signal is not None else None,
        "market_atr": _atr(candles[: index + 1], 14),
        "market_rolling_volatility": _std(rolling_returns) if len(rolling_returns) > 1 else None,
    }


def _ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    alpha = 2 / (period + 1)
    value = sum(values[:period]) / period
    for item in values[period:]:
        value = alpha * item + (1 - alpha) * value
    return value


def _std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((x - mean) ** 2 for x in values) / len(values))


def _rsi(closes: Sequence[float], period: int) -> float | None:
    if len(closes) <= period:
        return None
    differences = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
    gain = sum(max(x, 0) for x in differences) / period
    loss = sum(max(-x, 0) for x in differences) / period
    return 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss)


def _atr(candles: Sequence[Candle], period: int) -> float | None:
    if len(candles) <= period:
        return None
    values = []
    for previous, current in zip(candles[-period - 1 : -1], candles[-period:], strict=True):
        values.append(
            max(
                float(current.high - current.low),
                abs(float(current.high - previous.close)),
                abs(float(current.low - previous.close)),
            )
        )
    return sum(values) / len(values)
