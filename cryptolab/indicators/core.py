"""Technical indicators: ATR, EMA, SMA, RSI, ADX, Bollinger, slope-z, volume ratio."""

from typing import Optional, Dict, List
from dataclasses import dataclass


def compute_atr(candles: list, period: int = 14) -> Optional[float]:
    """ATR using Wilder's Smoothing (RMA). Aligns with TradingView."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i]["h"])
        l_ = float(candles[i]["l"])
        pc = float(candles[i - 1]["c"])
        trs.append(max(h - l_, abs(h - pc), abs(l_ - pc)))
    atr = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        atr = (atr * (period - 1) + trs[i]) / period
    return atr


def compute_ema(values: list, period: int) -> Optional[float]:
    if len(values) < period or period <= 0:
        return None
    k = 2.0 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * k + ema * (1 - k)
    return ema


def compute_sma(values: list, period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def compute_rsi(closes: list, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        delta = closes[i] - closes[i - 1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def compute_adx(candles: list, period: int = 14) -> Optional[Dict[str, float]]:
    """Compute ADX, +DI, -DI. Requires at least 2*period+1 candles."""
    n = len(candles)
    if n < 2 * period + 1:
        return None

    plus_dm_list, minus_dm_list, tr_list = [], [], []
    for i in range(1, n):
        h = float(candles[i]["h"])
        l = float(candles[i]["l"])
        ph = float(candles[i - 1]["h"])
        pl = float(candles[i - 1]["l"])
        pc = float(candles[i - 1]["c"])

        up_move = h - ph
        down_move = pl - l
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

        tr = max(h - l, abs(h - pc), abs(l - pc))
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)
        tr_list.append(tr)

    def wilder_smooth(data: list, p: int) -> list:
        result = []
        s = sum(data[:p])
        result.append(s)
        for i in range(p, len(data)):
            s = s - s / p + data[i]
            result.append(s)
        return result

    sm_plus = wilder_smooth(plus_dm_list, period)
    sm_minus = wilder_smooth(minus_dm_list, period)
    sm_tr = wilder_smooth(tr_list, period)

    dx_list = []
    for i in range(len(sm_tr)):
        tr_val = sm_tr[i]
        if tr_val == 0:
            dx_list.append(0)
            continue
        pdi = 100.0 * sm_plus[i] / tr_val
        mdi = 100.0 * sm_minus[i] / tr_val
        denom = pdi + mdi
        if denom == 0:
            dx_list.append(0)
        else:
            dx_list.append(100.0 * abs(pdi - mdi) / denom)

    if len(dx_list) < period:
        return None

    adx_val = sum(dx_list[:period]) / period
    for i in range(period, len(dx_list)):
        adx_val = (adx_val * (period - 1) + dx_list[i]) / period

    tr_last = sm_tr[-1] if sm_tr[-1] != 0 else 1e-9
    plus_di = 100.0 * sm_plus[-1] / tr_last
    minus_di = 100.0 * sm_minus[-1] / tr_last

    return {"adx": adx_val, "plus_di": plus_di, "minus_di": minus_di}


def compute_bollinger(closes: list, period: int = 20, std_mult: float = 2.0) -> Optional[Dict[str, float]]:
    if len(closes) < period:
        return None
    window = closes[-period:]
    mid = sum(window) / period
    std = (sum((x - mid) ** 2 for x in window) / period) ** 0.5
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    width = (upper - lower) / mid if mid != 0 else 0
    return {"upper": upper, "middle": mid, "lower": lower, "width": width, "std": std}


def compute_slope_z(closes: list, lookback: int = 20) -> Optional[float]:
    """Price slope z-score: linear regression slope / std."""
    if len(closes) < lookback:
        return None
    window = closes[-lookback:]
    x = list(range(lookback))
    x_mean = sum(x) / lookback
    y_mean = sum(window) / lookback
    numerator = sum((x[i] - x_mean) * (window[i] - y_mean) for i in range(lookback))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(lookback))
    if denominator == 0:
        return 0.0
    slope = numerator / denominator
    std = (sum((v - y_mean) ** 2 for v in window) / lookback) ** 0.5
    if std == 0:
        return 0.0
    return slope / std * (lookback ** 0.5)


def compute_tsmom(closes: list, lookback: int) -> Optional[float]:
    """Time-series momentum: return over lookback normalized by realized vol.

    Returns a score in [-1, 1]. Positive = upward momentum, negative = downward.
    """
    if len(closes) < lookback + 1 or lookback < 2:
        return None
    if closes[-lookback] <= 0:
        return 0.0
    ret = (closes[-1] - closes[-lookback]) / closes[-lookback]
    # Bar-to-bar returns over the lookback window
    start = max(1, len(closes) - lookback)
    rets = []
    for i in range(start, len(closes)):
        if closes[i - 1] > 0:
            rets.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(rets) < 2:
        return 0.0
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol = var ** 0.5
    if vol <= 0:
        return 0.0
    # Sharpe-like score, scaled so ~2.5 sigma maps to +/-1.0
    score = ret / (vol * lookback ** 0.5)
    return max(-1.0, min(1.0, score / 2.5))


def compute_volume_ratio(candles: list, lookback: int = 20) -> float:
    """Current volume / recent average volume."""
    if len(candles) < lookback + 1:
        return 1.0
    try:
        vols = [float(c.get("v", 0) or 0) for c in candles[-(lookback + 1):-1]]
        cur_v = float(candles[-1].get("v", 0) or 0)
    except (TypeError, ValueError):
        return 1.0
    avg_v = sum(vols) / max(len(vols), 1)
    if avg_v <= 0:
        return 1.0
    return cur_v / avg_v


@dataclass
class MarketSnapshot:
    """All market data and indicators for a symbol at a point in time."""
    symbol: str
    candles: list
    closes: List[float]
    highs: List[float]
    lows: List[float]
    volumes: List[float]
    last_close: float
    mark_px: float
    funding_rate: float

    atr: Optional[float] = None
    atr_pct: Optional[float] = None
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None
    rsi: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    ema_fast: Optional[float] = None
    ema_slow: Optional[float] = None
    slope_z: Optional[float] = None
    volume_ratio: float = 1.0


def build_market_snapshot(
    symbol: str,
    candles: list,
    mark_px: float,
    funding_rate: float,
    atr_period: int = 14,
    adx_period: int = 14,
    rsi_period: int = 14,
    bb_period: int = 20,
    bb_std_mult: float = 2.0,
    ema_fast_period: int = 20,
    ema_slow_period: int = 50,
    slope_lookback: int = 20,
    vol_lookback: int = 20,
) -> MarketSnapshot:
    """Build a complete market snapshot from candle data."""
    closes = [float(c["c"]) for c in candles]
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]
    volumes = [float(c.get("v", 0) or 0) for c in candles]
    last_close = closes[-1] if closes else 0.0

    snap = MarketSnapshot(
        symbol=symbol, candles=candles, closes=closes, highs=highs,
        lows=lows, volumes=volumes, last_close=last_close,
        mark_px=mark_px, funding_rate=funding_rate,
    )

    atr_val = compute_atr(candles, atr_period)
    snap.atr = atr_val
    snap.atr_pct = (atr_val / last_close) if (atr_val and last_close) else None

    adx_result = compute_adx(candles, adx_period)
    if adx_result:
        snap.adx = adx_result["adx"]
        snap.plus_di = adx_result["plus_di"]
        snap.minus_di = adx_result["minus_di"]

    snap.rsi = compute_rsi(closes, rsi_period)

    bb = compute_bollinger(closes, bb_period, bb_std_mult)
    if bb:
        snap.bb_upper = bb["upper"]
        snap.bb_middle = bb["middle"]
        snap.bb_lower = bb["lower"]
        snap.bb_width = bb["width"]

    snap.ema_fast = compute_ema(closes, ema_fast_period)
    snap.ema_slow = compute_ema(closes, ema_slow_period)
    snap.slope_z = compute_slope_z(closes, slope_lookback)
    snap.volume_ratio = compute_volume_ratio(candles, vol_lookback)

    return snap
