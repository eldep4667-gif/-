"""Technical analysis with ta library (minimal output)."""

import numpy as np
import pandas as pd
import ta
from scipy.signal import argrelextrema


class TechnicalAnalyzer:
    """Compute core indicators and clean technical context."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.indicators = {}
        self.support_levels = []
        self.resistance_levels = []
        self.trendline = {}
        self.stats = {}
        self._run()

    def _run(self):
        self._compute_indicators()
        self._find_support_resistance()
        self._build_trendline()
        self._compute_stats()

    def _compute_indicators(self):
        close = self.df["close"]
        high = self.df["high"]
        low = self.df["low"]

        self.indicators["ma20"] = ta.trend.sma_indicator(close, window=20)
        self.indicators["ma50"] = ta.trend.sma_indicator(close, window=50)
        self.indicators["rsi"] = ta.momentum.rsi(close, window=14)
        self.indicators["macd"] = ta.trend.macd(close)
        self.indicators["macd_signal"] = ta.trend.macd_signal(close)
        self.indicators["atr"] = ta.volatility.average_true_range(high, low, close, window=14)

    def _find_support_resistance(self):
        close = self.df["close"].values
        if len(close) < 30:
            return

        order = max(3, len(close) // 40)
        min_idx = argrelextrema(close, np.less, order=order)[0]
        max_idx = argrelextrema(close, np.greater, order=order)[0]

        supports = [close[i] for i in min_idx]
        resistances = [close[i] for i in max_idx]

        self.support_levels = self._cluster_levels(supports, threshold=0.0025)[:6]
        self.resistance_levels = self._cluster_levels(resistances, threshold=0.0025)[:6]

    def _cluster_levels(self, levels: list, threshold: float) -> list:
        if not levels:
            return []
        merged = []
        for lvl in sorted(levels):
            if not merged:
                merged.append(lvl)
                continue
            if abs(lvl - merged[-1]) / max(merged[-1], 1e-9) <= threshold:
                merged[-1] = (merged[-1] + lvl) / 2
            else:
                merged.append(lvl)
        return merged

    def _build_trendline(self):
        close = self.df["close"].values
        if len(close) < 20:
            self.trendline = {"slope": 0.0, "direction": "Neutral"}
            return
        x = np.arange(len(close))
        slope, intercept = np.polyfit(x, close, 1)
        direction = "Bullish" if slope > 0 else "Bearish"
        self.trendline = {
            "slope": float(slope),
            "intercept": float(intercept),
            "direction": direction,
        }

    def _compute_stats(self):
        ret = self.df["close"].pct_change().dropna()
        if ret.empty:
            self.stats = {"volatility": 0.0, "trend_score": 50}
            return
        trend_score = 50
        if self.trendline["direction"] == "Bullish":
            trend_score += 20
        rsi = float(self.indicators["rsi"].iloc[-1]) if not self.indicators["rsi"].empty else 50
        trend_score += 10 if 45 <= rsi <= 65 else -5
        self.stats = {
            "volatility": round(ret.std() * np.sqrt(252) * 100, 2),
            "trend_score": max(0, min(100, trend_score)),
        }

    def get_indicators_snapshot(self) -> dict:
        close = float(self.df["close"].iloc[-1])
        rsi = float(self.indicators["rsi"].iloc[-1]) if not self.indicators["rsi"].empty else 50.0
        macd = float(self.indicators["macd"].iloc[-1]) if not self.indicators["macd"].empty else 0.0
        macd_sig = float(self.indicators["macd_signal"].iloc[-1]) if not self.indicators["macd_signal"].empty else 0.0
        ma20 = float(self.indicators["ma20"].iloc[-1]) if not self.indicators["ma20"].empty else close
        ma50 = float(self.indicators["ma50"].iloc[-1]) if not self.indicators["ma50"].empty else close
        return {
            "close": close,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_sig,
            "ma20": ma20,
            "ma50": ma50,
            "trendline_direction": self.trendline.get("direction", "Neutral"),
        }
