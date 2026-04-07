"""Mode-aware decision engine that differentiates SMC, ICT, and SK analysis."""

from __future__ import annotations

import math

import pandas as pd


class AISignalEngine:
    """Generate school-specific trade analysis with transparent rationale."""

    def __init__(self, df: pd.DataFrame, technical, pattern_detector, schools, news_summary: dict | None = None):
        self.df = df.copy()
        self.technical = technical
        self.pattern_detector = pattern_detector
        self.schools = schools
        self.news_summary = news_summary or {}

    def generate_signal(self, mode: str = "SMART") -> dict:
        snapshot = self.technical.get_indicators_snapshot()
        current = float(snapshot["close"])
        atr = float(self.technical.indicators["atr"].iloc[-1]) if not self.technical.indicators["atr"].empty else current * 0.004
        atr = max(atr, current * 0.0015)

        core_details: list[dict] = []
        school_details: list[dict] = []

        core_score = self._score_core_context(snapshot, current, atr, core_details)
        school_score, school_meta = self._score_mode(mode, current, atr, school_details)
        news_score = self._score_news(core_details)
        pattern_score = self._score_patterns(core_details)

        mode_mix = {
            "SMART": (0.9, 1.0),
            "SMC": (0.45, 1.4),
            "ICT": (0.45, 1.35),
            "SK": (0.55, 1.25),
        }
        core_weight, school_weight = mode_mix.get(mode, (0.8, 1.0))
        score = core_score * core_weight + school_score * school_weight + news_score + pattern_score * 0.55

        action = "WAIT"
        threshold = {"SMART": 1.35, "SMC": 1.1, "ICT": 1.1, "SK": 1.0}.get(mode, 1.25)
        if score >= threshold:
            action = "BUY"
        elif score <= -threshold:
            action = "SELL"

        details = school_details + core_details
        entry_low, entry_high = self._entry_zone(current, atr, action, school_meta)
        sl, tp = self._risk_targets(current, atr, action, school_meta)
        risk = max(abs(current - sl), 1e-9)
        reward = abs(tp - current)
        bias = "Bullish" if score > 0.25 else "Bearish" if score < -0.25 else "Neutral"
        confidence = self._confidence(score, details, mode)
        conflicts = sum(1 for item in details if item["direction"] == "conflict")

        return {
            "decision": action,
            "bias": bias,
            "entry": round(current, 5),
            "entry_zone": f"{entry_low:.5f} - {entry_high:.5f}",
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "rr": round(reward / risk, 2),
            "confidence": confidence,
            "score": round(score, 2),
            "confluence_score": round(abs(score) * 20, 1),
            "mode": mode,
            "mode_title": school_meta.get("title", mode),
            "strategy_focus": school_meta.get("focus", "Multi-factor confluence"),
            "news_impact": self.news_summary.get("impact_label", "Unknown"),
            "news_bias": self.news_summary.get("sentiment", "neutral"),
            "reason": self._headline_reason(mode, action, school_details, core_details),
            "invalidations": self._invalidations(action, mode, school_meta),
            "tp_sl_rationale": self._tp_sl_rationale(mode, action, atr, school_meta),
            "school_summary": school_meta.get("summary", ""),
            "details": details,
            "conflicts": conflicts,
        }

    def _score_core_context(self, snapshot: dict, current: float, atr: float, details: list[dict]) -> float:
        score = 0.0
        ma20 = float(snapshot["ma20"])
        ma50 = float(snapshot["ma50"])
        rsi = float(snapshot["rsi"])
        macd = float(snapshot["macd"])
        macd_signal = float(snapshot["macd_signal"])
        trendline = snapshot["trendline_direction"]

        if current > ma20 > ma50:
            score += 1.1
            details.append(self._detail("Trend Alignment", "bullish", 1.1, "Price is above MA20 and MA50 with positive structural alignment."))
        elif current < ma20 < ma50:
            score -= 1.1
            details.append(self._detail("Trend Alignment", "bearish", 1.1, "Price is below MA20 and MA50 with negative structural alignment."))
        else:
            details.append(self._detail("Trend Alignment", "conflict", 0.45, "Moving-average structure is mixed and not fully aligned."))

        if rsi >= 58:
            score += 0.7
            details.append(self._detail("RSI Regime", "bullish", 0.7, f"RSI at {rsi:.1f} supports stronger upside participation."))
        elif rsi <= 42:
            score -= 0.7
            details.append(self._detail("RSI Regime", "bearish", 0.7, f"RSI at {rsi:.1f} supports downside pressure."))
        else:
            details.append(self._detail("RSI Regime", "conflict", 0.3, f"RSI at {rsi:.1f} is neutral and not providing clear momentum."))

        if macd > macd_signal:
            score += 0.55
            details.append(self._detail("MACD Confirmation", "bullish", 0.55, "MACD remains above signal and confirms bullish momentum."))
        else:
            score -= 0.55
            details.append(self._detail("MACD Confirmation", "bearish", 0.55, "MACD remains below signal and confirms bearish momentum."))

        if trendline == "Bullish":
            score += 0.45
            details.append(self._detail("Trend Slope", "bullish", 0.45, "Trend slope still leans upward on the active sample."))
        else:
            score -= 0.45
            details.append(self._detail("Trend Slope", "bearish", 0.45, "Trend slope still leans downward on the active sample."))

        support = float(self.schools.ta_summary.get("support", current))
        resistance = float(self.schools.ta_summary.get("resistance", current))
        if current - support <= atr * 1.15:
            score += 0.25
            details.append(self._detail("Support Proximity", "bullish", 0.25, "Price is trading near support, which can help long reactions."))
        if resistance - current <= atr * 1.15:
            score -= 0.25
            details.append(self._detail("Resistance Proximity", "bearish", 0.25, "Price is trading near resistance, limiting upside room."))

        return score

    def _score_mode(self, mode: str, current: float, atr: float, details: list[dict]) -> tuple[float, dict]:
        if mode == "SMC":
            return self._score_smc(current, atr, details)
        if mode == "ICT":
            return self._score_ict(current, atr, details)
        if mode == "SK":
            return self._score_sk(current, atr, details)

        smc_score, smc_meta = self._score_smc(current, atr, details)
        ict_score, ict_meta = self._score_ict(current, atr, details)
        sk_score, sk_meta = self._score_sk(current, atr, details)
        smart_meta = {
            "title": "Smart AI",
            "focus": "Balanced fusion of SMC, ICT, SK, and momentum context.",
            "summary": "Smart mode combines structure, timing, and trend-following evidence to choose the dominant side.",
            "entry_bias": self._first_non_empty(
                smc_meta.get("entry_bias"),
                ict_meta.get("entry_bias"),
                sk_meta.get("entry_bias"),
            ),
        }
        return (smc_score * 0.38 + ict_score * 0.34 + sk_score * 0.28), smart_meta

    def _score_smc(self, current: float, atr: float, details: list[dict]) -> tuple[float, dict]:
        smc = self.schools.smc_analysis
        score = 0.0
        structure = smc.get("market_structure", "Neutral")
        if structure == "Bullish":
            score += 1.1
            details.append(self._detail("SMC Market Structure", "bullish", 1.1, "Structure is bullish and favors continuation from demand."))
        elif structure == "Bearish":
            score -= 1.1
            details.append(self._detail("SMC Market Structure", "bearish", 1.1, "Structure is bearish and favors continuation from supply."))

        last_bos = self._first(smc.get("bos", []), from_end=True)
        if last_bos:
            bullish = "bullish" in last_bos.get("type", "")
            score += 1.0 if bullish else -1.0
            details.append(self._detail("Break of Structure", "bullish" if bullish else "bearish", 1.0, "Latest BOS confirms the current institutional directional break."))

        active_ob = smc.get("active_order_block")
        if active_ob:
            bullish = active_ob.get("type") == "bullish"
            distance = abs(current - active_ob.get("mid", current))
            weight = 0.9 if distance <= atr * 1.5 else 0.45
            score += weight if bullish else -weight
            details.append(self._detail("Order Block Reaction", "bullish" if bullish else "bearish", weight, "Nearest order block is still the key SMC reaction zone."))

        choch = smc.get("choch", "Not clear")
        if choch == "Detected":
            details.append(self._detail("CHoCH Context", "conflict", 0.45, "Change of character detected, so continuation and reversal scenarios both matter."))

        sweep = smc.get("liquidity_sweep", "")
        if "buy-side" in sweep.lower():
            score -= 0.35
            details.append(self._detail("Liquidity Sweep", "bearish", 0.35, "Price is close to buy-side liquidity, so upside may be used for a sweep before reversing."))
        elif "sell-side" in sweep.lower():
            score += 0.35
            details.append(self._detail("Liquidity Sweep", "bullish", 0.35, "Price is close to sell-side liquidity, so downside may be used to grab liquidity before reversing."))

        entry_zones = smc.get("entry_zones", {})
        meta = {
            "title": "SMC",
            "focus": "Break of structure, liquidity, order blocks, and imbalance.",
            "summary": "SMC mode reads institutional flow through BOS, order blocks, liquidity, and possible character shifts.",
            "entry_bias": "buy_zone" if entry_zones.get("buy_zone") else "sell_zone" if entry_zones.get("sell_zone") else None,
            "entry_zones": entry_zones,
        }
        return score, meta

    def _score_ict(self, current: float, atr: float, details: list[dict]) -> tuple[float, dict]:
        ict = self.schools.ict_analysis
        score = 0.0

        daily_bias = ict.get("daily_bias", "Neutral")
        if "Bullish" in daily_bias:
            score += 1.0
            details.append(self._detail("ICT Daily Bias", "bullish", 1.0, "Price sits in discount territory, which supports bullish ICT bias."))
        elif "Bearish" in daily_bias:
            score -= 1.0
            details.append(self._detail("ICT Daily Bias", "bearish", 1.0, "Price sits in premium territory, which supports bearish ICT bias."))
        else:
            details.append(self._detail("ICT Daily Bias", "conflict", 0.35, "Price is around equilibrium, so daily bias is not decisive."))

        displacement = ict.get("displacement", "No significant displacement")
        if "Bullish" in displacement:
            score += 0.75
            details.append(self._detail("Displacement", "bullish", 0.75, "Bullish displacement suggests strong smart-money expansion."))
        elif "Bearish" in displacement:
            score -= 0.75
            details.append(self._detail("Displacement", "bearish", 0.75, "Bearish displacement suggests strong smart-money expansion downward."))

        po3 = ict.get("power_of_3", "")
        if "Accumulation" in po3:
            details.append(self._detail("Power of 3", "conflict", 0.45, "Accumulation phase means the real move may still be building."))
        elif "Bullish" in po3 or po3.endswith("Up"):
            score += 0.55
            details.append(self._detail("Power of 3", "bullish", 0.55, "Power-of-3 context currently supports upward delivery."))
        elif "Bearish" in po3 or po3.endswith("Down"):
            score -= 0.55
            details.append(self._detail("Power of 3", "bearish", 0.55, "Power-of-3 context currently supports downward delivery."))

        ote = ict.get("ote", {})
        ote_status = ote.get("status", "")
        if "IN OTE Zone" in ote_status:
            score += 0.85 if "Bullish" in daily_bias else -0.85 if "Bearish" in daily_bias else 0.25
            details.append(self._detail("OTE Zone", "bullish" if "Bullish" in daily_bias else "bearish" if "Bearish" in daily_bias else "conflict", 0.85, "Price is inside the ICT optimal trade entry zone."))
        elif "Below OTE" in ote_status or "Above OTE" in ote_status:
            details.append(self._detail("OTE Zone", "conflict", 0.35, "Price is outside the ideal ICT retracement zone and timing is less efficient."))

        nwog = ict.get("nwog", "N/A")
        if "Bullish" in nwog:
            score += 0.25
            details.append(self._detail("NWOG Context", "bullish", 0.25, "The weekly gap context slightly supports bullish continuation."))
        elif "Bearish" in nwog:
            score -= 0.25
            details.append(self._detail("NWOG Context", "bearish", 0.25, "The weekly gap context slightly supports bearish continuation."))

        meta = {
            "title": "ICT",
            "focus": "Daily bias, displacement, OTE timing, and delivery narrative.",
            "summary": "ICT mode emphasizes timing through premium/discount bias, displacement, OTE, PO3, and gap context.",
            "entry_bias": daily_bias,
            "ote": ote,
        }
        return score, meta

    def _score_sk(self, current: float, atr: float, details: list[dict]) -> tuple[float, dict]:
        sk = self.schools.sk_analysis
        score = 0.0

        structure = sk.get("market_structure", "Neutral")
        if structure == "Bullish":
            score += 0.95
            details.append(self._detail("SK Structure", "bullish", 0.95, "SK market structure remains bullish and trend-following still favors longs."))
        elif structure == "Bearish":
            score -= 0.95
            details.append(self._detail("SK Structure", "bearish", 0.95, "SK market structure remains bearish and trend-following still favors shorts."))

        phase = sk.get("phase", "")
        if "Uptrend" in phase:
            score += 0.7
            details.append(self._detail("SK Phase", "bullish", 0.7, "Market is in SK uptrend phase and continuation setups have better odds."))
        elif "Downtrend" in phase:
            score -= 0.7
            details.append(self._detail("SK Phase", "bearish", 0.7, "Market is in SK downtrend phase and continuation shorts have better odds."))
        else:
            details.append(self._detail("SK Phase", "conflict", 0.35, "Market is in a transition or pullback phase, so timing matters more."))

        signal = sk.get("signal", "N/A")
        if "BUY" in signal:
            score += 0.85
            details.append(self._detail("SK Signal", "bullish", 0.85, "EMA and RSI conditions align for an SK buy continuation."))
        elif "SELL" in signal:
            score -= 0.85
            details.append(self._detail("SK Signal", "bearish", 0.85, "EMA and RSI conditions align for an SK sell continuation."))
        else:
            details.append(self._detail("SK Signal", "conflict", 0.3, "SK setup is neutral and waiting for cleaner confirmation."))

        quality = sk.get("quality", "")
        if quality.startswith("A+"):
            score += 0.4 if structure == "Bullish" else -0.4 if structure == "Bearish" else 0.0
            details.append(self._detail("SK Setup Quality", "bullish" if structure == "Bullish" else "bearish" if structure == "Bearish" else "conflict", 0.4, "Current SK setup quality is high relative to its RSI regime."))
        elif quality.startswith("C"):
            details.append(self._detail("SK Setup Quality", "conflict", 0.35, "Setup quality is stretched and needs caution before entry."))

        meta = {
            "title": "SK",
            "focus": "Trend phase, EMA pullback logic, and momentum continuation.",
            "summary": "SK mode is trend-following first: it values phase, continuation signal, pullback logic, and setup quality.",
            "entry_bias": signal,
            "key_levels": sk.get("key_levels", []),
        }
        return score, meta

    def _score_patterns(self, details: list[dict]) -> float:
        pattern = self.pattern_detector.detected_patterns[0] if self.pattern_detector.detected_patterns else None
        if not pattern:
            details.append(self._detail("Pattern Context", "conflict", 0.2, "No high-confidence harmonic pattern is active right now."))
            return 0.0
        direction = 1 if pattern.get("signal") == "buy" else -1
        weight = min(0.8, pattern.get("confidence", 0) / 100 * 0.8)
        details.append(self._detail(f"{pattern.get('name', 'Pattern')} Pattern", "bullish" if direction > 0 else "bearish", weight, f"Harmonic structure is active with {pattern.get('confidence', 0):.0f}% confidence."))
        return direction * weight

    def _score_news(self, details: list[dict]) -> float:
        sentiment = self.news_summary.get("sentiment", "neutral")
        impact = self.news_summary.get("impact_label", "Unknown")
        magnitude = {"Low": 0.15, "Medium": 0.35, "High": 0.55, "Unknown": 0.0}.get(impact, 0.0)
        if sentiment == "positive":
            details.append(self._detail("News Flow", "bullish", magnitude, "Recent headlines lean supportive for the selected instrument."))
            return magnitude
        if sentiment == "negative":
            details.append(self._detail("News Flow", "bearish", magnitude, "Recent headlines lean negative for the selected instrument."))
            return -magnitude
        details.append(self._detail("News Flow", "conflict", 0.2, "News flow is mixed or low conviction, so it is not confirming strongly."))
        return 0.0

    def _entry_zone(self, current: float, atr: float, action: str, school_meta: dict) -> tuple[float, float]:
        width = atr * 0.45
        if action == "BUY":
            return current - width, current + atr * 0.2
        if action == "SELL":
            return current - atr * 0.2, current + width
        return current - width, current + width

    def _risk_targets(self, current: float, atr: float, action: str, school_meta: dict) -> tuple[float, float]:
        if action == "BUY":
            return current - atr * 1.45, current + atr * 2.75
        if action == "SELL":
            return current + atr * 1.45, current - atr * 2.75
        return current - atr * 1.1, current + atr * 1.1

    def _confidence(self, score: float, details: list[dict], mode: str) -> float:
        bullish = sum(item["weight"] for item in details if item["direction"] == "bullish")
        bearish = sum(item["weight"] for item in details if item["direction"] == "bearish")
        conflict = sum(item["weight"] for item in details if item["direction"] == "conflict")
        edge = abs(bullish - bearish)
        mode_bonus = {"SMART": 0.0, "SMC": 2.0, "ICT": 2.0, "SK": 1.0}.get(mode, 0.0)
        confidence = 50 + edge * 10.5 + abs(score) * 7 - conflict * 4 + mode_bonus
        return round(max(45.0, min(93.0, confidence)), 1)

    def _headline_reason(self, mode: str, action: str, school_details: list[dict], core_details: list[dict]) -> str:
        strong_school = [item["signal"] for item in school_details if item["direction"] in {"bullish", "bearish"}][:3]
        core = [item["signal"] for item in core_details if item["direction"] in {"bullish", "bearish"}][:2]
        if not strong_school and not core:
            return "Signals are mixed and there is no decisive confluence yet."
        prefix = {
            "BUY": f"{mode} long setup",
            "SELL": f"{mode} short setup",
            "WAIT": f"{mode} setup is not ready",
        }.get(action, f"{mode} setup")
        joined = ", ".join(strong_school + core)
        return f"{prefix} backed by {joined}."

    def _invalidations(self, action: str, mode: str, school_meta: dict) -> str:
        if action == "BUY":
            return f"Invalidate the {mode} long if price loses the key demand/structure zone and closes below support."
        if action == "SELL":
            return f"Invalidate the {mode} short if price reclaims the key supply/structure zone and closes above resistance."
        return f"Wait until {mode} timing and momentum align before committing."

    def _tp_sl_rationale(self, mode: str, action: str, atr: float, school_meta: dict) -> str:
        if action == "WAIT":
            return f"{mode} remains in observation mode, so the dashboard keeps a neutral ATR envelope around {atr:.5f}."
        return f"{mode} stop loss is anchored near 1.45 ATR and take profit near 2.75 ATR to keep the setup disciplined while preserving upside."

    def _detail(self, signal: str, direction: str, weight: float, description: str) -> dict:
        normalized = max(0.0, min(1.35, float(weight)))
        return {
            "signal": signal,
            "direction": direction,
            "weight": round(normalized, 2),
            "desc": description,
            "strength": math.floor(normalized / 1.35 * 100),
        }

    def _first(self, values: list[dict], from_end: bool = False) -> dict | None:
        if not values:
            return None
        return values[-1] if from_end else values[0]

    def _first_non_empty(self, *values):
        for value in values:
            if value:
                return value
        return None
