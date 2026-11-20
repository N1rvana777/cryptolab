"""Technical indicator features: ATR, RSI, Bollinger, ADX, MACD, EMA ratios, etc.

All indicators use .shift(1) on OHLCV to prevent look-ahead bias:
features at bar t are computed from data available at bar t-1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from cryptolab.features.base import FeatureBlock


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (RMA): same as EMA with alpha=1/period."""
    return series.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, min_periods=period, adjust=False).mean()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def _true_range(high: pd.Series, low: pd.Series, prev_close: pd.Series) -> pd.Series:
    return pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close.shift(1))
    return _wilder_smooth(tr, period)


def _rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = _wilder_smooth(gain, period)
    avg_loss = _wilder_smooth(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


class TechnicalFeatures(FeatureBlock):
    """~40 technical indicator features."""

    ATR_PERIODS = [6, 14, 24, 72]
    RSI_PERIODS = [6, 14, 24]
    BB_PERIODS = [20, 50]
    EMA_PAIRS = [(8, 21), (12, 26), (21, 55)]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        # Shift OHLCV by 1 bar to prevent leakage
        o = df["open"].shift(1)
        h = df["high"].shift(1)
        l = df["low"].shift(1)   # noqa: E741
        c = df["close"].shift(1)
        v = df["volume"].shift(1)

        # --- ATR at multiple periods ---
        for p in self.ATR_PERIODS:
            atr = _atr(h, l, c, p)
            df[f"atr_{p}"] = atr
            df[f"atr_pct_{p}"] = atr / c.replace(0, np.nan)

        # --- RSI at multiple periods ---
        for p in self.RSI_PERIODS:
            df[f"rsi_{p}"] = _rsi(c, p)

        # --- ADX (14) ---
        self._compute_adx(df, h, l, c, period=14)

        # --- Bollinger Bands ---
        for p in self.BB_PERIODS:
            mid = _sma(c, p)
            std = c.rolling(p, min_periods=p).std()
            upper = mid + 2.0 * std
            lower = mid - 2.0 * std
            df[f"bb_width_{p}"] = (upper - lower) / mid.replace(0, np.nan)
            df[f"bb_pctb_{p}"] = (c - lower) / (upper - lower).replace(0, np.nan)

        # --- EMA ratios ---
        for fast, slow in self.EMA_PAIRS:
            ema_f = _ema(c, fast)
            ema_s = _ema(c, slow)
            df[f"ema_ratio_{fast}_{slow}"] = ema_f / ema_s.replace(0, np.nan) - 1.0

        # --- MACD (12, 26, 9) ---
        ema12 = _ema(c, 12)
        ema26 = _ema(c, 26)
        macd_line = ema12 - ema26
        macd_signal = _ema(macd_line, 9)
        df["macd_hist"] = (macd_line - macd_signal) / c.replace(0, np.nan)

        # --- Stochastic Oscillator (14, 3) ---
        low_14 = l.rolling(14, min_periods=14).min()
        high_14 = h.rolling(14, min_periods=14).max()
        denom = (high_14 - low_14).replace(0, np.nan)
        stoch_k = (c - low_14) / denom * 100
        df["stoch_k"] = stoch_k
        df["stoch_d"] = stoch_k.rolling(3, min_periods=3).mean()

        # --- Williams %R (14) ---
        df["williams_r"] = (high_14 - c) / denom * -100

        # --- CCI (14, 24) ---
        for p in [14, 24]:
            tp = (h + l + c) / 3
            tp_sma = _sma(tp, p)
            mad = tp.rolling(p, min_periods=p).apply(
                lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
            )
            df[f"cci_{p}"] = (tp - tp_sma) / (0.015 * mad.replace(0, np.nan))

        # --- OBV slope ---
        obv_direction = np.sign(c.diff())
        obv = (v * obv_direction).cumsum()
        df["obv_slope_14"] = obv.diff(14) / obv.rolling(14).mean().replace(0, np.nan)

        return df

    def _compute_adx(self, df: pd.DataFrame, h: pd.Series, l: pd.Series,
                     c: pd.Series, period: int = 14) -> None:
        """Compute ADX, +DI, -DI using Wilder's smoothing."""
        up_move = h.diff()
        down_move = -l.diff()

        plus_dm = pd.Series(np.where(
            (up_move > down_move) & (up_move > 0), up_move, 0.0
        ), index=h.index)
        minus_dm = pd.Series(np.where(
            (down_move > up_move) & (down_move > 0), down_move, 0.0
        ), index=h.index)

        tr = _true_range(h, l, c.shift(1))
        sm_tr = _wilder_smooth(tr, period)
        sm_plus = _wilder_smooth(plus_dm, period)
        sm_minus = _wilder_smooth(minus_dm, period)

        plus_di = 100.0 * sm_plus / sm_tr.replace(0, np.nan)
        minus_di = 100.0 * sm_minus / sm_tr.replace(0, np.nan)

        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = _wilder_smooth(dx, period)

        df["adx"] = adx
        df["plus_di"] = plus_di
        df["minus_di"] = minus_di

    def feature_names(self) -> list[str]:
        names = []
        for p in self.ATR_PERIODS:
            names.extend([f"atr_{p}", f"atr_pct_{p}"])
        for p in self.RSI_PERIODS:
            names.append(f"rsi_{p}")
        names.extend(["adx", "plus_di", "minus_di"])
        for p in self.BB_PERIODS:
            names.extend([f"bb_width_{p}", f"bb_pctb_{p}"])
        for fast, slow in self.EMA_PAIRS:
            names.append(f"ema_ratio_{fast}_{slow}")
        names.append("macd_hist")
        names.extend(["stoch_k", "stoch_d", "williams_r"])
        for p in [14, 24]:
            names.append(f"cci_{p}")
        names.append("obv_slope_14")
        return names
