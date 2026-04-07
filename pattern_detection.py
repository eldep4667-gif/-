"""Harmonic pattern detector (Gartley/Bat/Butterfly/Crab only)."""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


class PatternDetector:
    """Detect advanced harmonic patterns and PRZ zones."""

    _RATIOS = {
        "Gartley": {"ab_xa": (0.55, 0.68), "bc_ab": (0.382, 0.886), "cd_xa": (0.74, 0.84)},
        "Bat": {"ab_xa": (0.35, 0.52), "bc_ab": (0.382, 0.886), "cd_xa": (0.84, 0.93)},
        "Butterfly": {"ab_xa": (0.75, 0.82), "bc_ab": (0.382, 0.886), "cd_xa": (1.20, 1.70)},
        "Crab": {"ab_xa": (0.35, 0.70), "bc_ab": (0.382, 0.886), "cd_xa": (1.50, 1.75)},
    }

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.detected_patterns = []
        self._run()

    def _run(self):
        prices = self.df["close"].values
        if len(prices) < 80:
            return

        order = max(3, len(prices) // 45)
        highs = argrelextrema(prices, np.greater, order=order)[0]
        lows = argrelextrema(prices, np.less, order=order)[0]
        pivots = sorted(np.concatenate([highs, lows]).tolist())
        pivots = pivots[-35:]
        if len(pivots) < 5:
            return

        for i in range(len(pivots) - 4):
            x, a, b, c, d = pivots[i:i + 5]
            px = prices[x]
            pa = prices[a]
            pb = prices[b]
            pc = prices[c]
            pd_ = prices[d]
            xa = pa - px
            ab = pb - pa
            bc = pc - pb
            cd = pd_ - pc
            if min(abs(xa), abs(ab), abs(bc), abs(cd)) <= 1e-9:
                continue

            bullish = xa < 0 and ab > 0 and bc < 0 and cd > 0
            bearish = xa > 0 and ab < 0 and bc > 0 and cd < 0
            if not (bullish or bearish):
                continue

            ab_xa = abs(ab / xa)
            bc_ab = abs(bc / ab)
            cd_xa = abs((pd_ - px) / xa)
            for pattern, ranges in self._RATIOS.items():
                score = self._score_pattern(ab_xa, bc_ab, cd_xa, ranges)
                if score < 70:
                    continue
                prz_half_width = abs(pc - pd_) * 0.25
                prz_low = min(pd_ - prz_half_width, pd_ + prz_half_width)
                prz_high = max(pd_ - prz_half_width, pd_ + prz_half_width)
                signal = "buy" if bullish else "sell"
                self.detected_patterns.append(
                    {
                        "name": pattern,
                        "signal": signal,
                        "confidence": round(score, 1),
                        "idx": int(d),
                        "price": float(pd_),
                        "prz_low": float(prz_low),
                        "prz_high": float(prz_high),
                        "ratios": {
                            "AB/XA": round(ab_xa, 3),
                            "BC/AB": round(bc_ab, 3),
                            "CD/XA": round(cd_xa, 3),
                        },
                    }
                )

        self.detected_patterns.sort(key=lambda x: x["confidence"], reverse=True)
        self.detected_patterns = self.detected_patterns[:6]

    def _score_pattern(self, ab_xa: float, bc_ab: float, cd_xa: float, ranges: dict) -> float:
        center_ab = sum(ranges["ab_xa"]) / 2
        center_bc = sum(ranges["bc_ab"]) / 2
        center_cd = sum(ranges["cd_xa"]) / 2
        span_ab = max((ranges["ab_xa"][1] - ranges["ab_xa"][0]) / 2, 1e-9)
        span_bc = max((ranges["bc_ab"][1] - ranges["bc_ab"][0]) / 2, 1e-9)
        span_cd = max((ranges["cd_xa"][1] - ranges["cd_xa"][0]) / 2, 1e-9)

        dev_ab = abs(ab_xa - center_ab) / span_ab
        dev_bc = abs(bc_ab - center_bc) / span_bc
        dev_cd = abs(cd_xa - center_cd) / span_cd
        avg_dev = (dev_ab + dev_bc + dev_cd) / 3
        return max(0.0, min(99.0, 100 - (avg_dev * 28)))
