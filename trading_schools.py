"""Focused trading schools analysis (SMC/ICT/SK/Technical)."""

import numpy as np
import pandas as pd


class TradingSchoolsAnalyzer:
    """Compute concise results for each trading school."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.smc_analysis = {}
        self.ict_analysis = {}
        self.sk_analysis = {}
        self.ta_summary = {}
        self._analyze_all()

    def _analyze_all(self):
        self._analyze_smc()
        self._analyze_ict()
        self._analyze_sk()
        self._analyze_ta()

    # ══════════════════════════════════════════════════════════════
    #          SMART MONEY CONCEPTS (SMC)
    # ══════════════════════════════════════════════════════════════
    def _analyze_smc(self):
        df = self.df
        close = df["close"]
        high = df["high"]
        low = df["low"]
        current = close.iloc[-1]

        order_blocks = self._find_order_blocks(df)
        bos = self._find_bos(close, high, low)
        choch = "Detected" if len(bos) >= 2 and bos[-1]["type"] != bos[-2]["type"] else "Not clear"
        liq_above = float(high.tail(50).max())
        liq_below = float(low.tail(50).min())
        inducement = "Possible" if abs(current - liq_above) / current < 0.003 or abs(current - liq_below) / current < 0.003 else "Low"
        market_structure = self._smc_market_structure(close, high, low)
        entry_zones = self._smc_entry_zones(order_blocks, market_structure)
        nearest_ob = order_blocks[0] if order_blocks else None
        liquidity_sweep = "Potential buy-side sweep" if abs(current - liq_above) / current < 0.002 else "Potential sell-side sweep" if abs(current - liq_below) / current < 0.002 else "Not near liquidity"

        self.smc_analysis = {
            "order_blocks": order_blocks[:4],
            "fvg": self._find_fair_value_gaps(df)[:4],
            "liquidity_zones": {"above": liq_above, "below": liq_below},
            "inducement": inducement,
            "bos": bos[-4:],
            "choch": choch,
            "market_structure": market_structure,
            "entry_zones": entry_zones,
            "liquidity_sweep": liquidity_sweep,
            "active_order_block": nearest_ob,
        }

    def _smc_market_structure(self, close, high, low) -> str:
        """Determine SMC market structure."""
        if len(close) < 20:
            return "Neutral"
        return "Bullish" if close.iloc[-1] > close.rolling(20).mean().iloc[-1] else "Bearish"

    def _find_order_blocks(self, df: pd.DataFrame) -> list:
        """
        Find institutional order blocks:
        A bullish OB is the last bearish candle before a strong upward move.
        A bearish OB is the last bullish candle before a strong downward move.
        """
        order_blocks = []
        close = df['close'].values
        open_ = df['open'].values
        high  = df['high'].values
        low   = df['low'].values
        n     = len(df)

        lookback = min(100, n - 5)
        threshold = 0.002  # minimum move to qualify

        for i in range(n - lookback, n - 3):
            body = abs(close[i] - open_[i])
            avg_body = np.mean(np.abs(close[max(0,i-10):i] - open_[max(0,i-10):i])) + 1e-10

            # Strong follow-through candle after
            next_move = (close[i+2] - close[i]) / close[i]

            # Bullish OB: bearish candle before bullish surge
            if close[i] < open_[i] and next_move > threshold:
                order_blocks.append({
                    'type': 'bullish',
                    'start': max(0, i - 1),
                    'end': min(n - 1, i + 4),
                    'high': high[i],
                    'low': low[i],
                    'mid': (high[i] + low[i]) / 2,
                    'strength': min(abs(next_move) * 100, 5)
                })

            # Bearish OB: bullish candle before bearish plunge
            elif close[i] > open_[i] and next_move < -threshold:
                order_blocks.append({
                    'type': 'bearish',
                    'start': max(0, i - 1),
                    'end': min(n - 1, i + 4),
                    'high': high[i],
                    'low': low[i],
                    'mid': (high[i] + low[i]) / 2,
                    'strength': min(abs(next_move) * 100, 5)
                })

        order_blocks = sorted(order_blocks, key=lambda x: x["start"], reverse=True)[:8]
        return order_blocks

    def _find_bos(self, close, high, low) -> list:
        """Detect Break of Structure events."""
        bos = []
        n   = len(close)
        lookback_window = min(20, n // 5)

        for i in range(lookback_window, n):
            prev_high = high.iloc[i-lookback_window:i].max()
            prev_low  = low.iloc[i-lookback_window:i].min()
            curr      = close.iloc[i]

            if curr > prev_high:
                bos.append({'type': 'bullish_bos', 'idx': i, 'level': prev_high})
            elif curr < prev_low:
                bos.append({'type': 'bearish_bos', 'idx': i, 'level': prev_low})

        return bos[-5:]

    def _smc_entry_zones(self, order_blocks: list, trend: str) -> dict:
        """Determine optimal SMC entry zones based on order blocks."""
        buy_obs  = [ob for ob in order_blocks if ob['type'] == 'bullish']
        sell_obs = [ob for ob in order_blocks if ob['type'] == 'bearish']

        result = {}

        if buy_obs and 'Bullish' in trend:
            best_buy = buy_obs[0]
            result['buy_zone'] = (best_buy['low'], best_buy['high'])

        if sell_obs and 'Bearish' in trend:
            best_sell = sell_obs[0]
            result['sell_zone'] = (best_sell['low'], best_sell['high'])

        return result


    def _analyze_ict(self):
        df = self.df
        close = df["close"]
        high = df["high"]
        low = df["low"]
        daily_bias = self._determine_daily_bias(close, high, low)
        displacement = self._detect_displacement(close, high, low)
        power_of_3 = self._power_of_3(close)
        ote = self._calculate_ote(close, high, low)
        nwog = self._find_nwog(df)
        self.ict_analysis = {
            "order_blocks": self._find_order_blocks(df)[:3],
            "fvg": self._find_fair_value_gaps(df)[:5],
            "liquidity_zones": {"above": float(high.tail(30).max()), "below": float(low.tail(30).min())},
            "inducement": "Watch sweep" if abs(close.iloc[-1] - high.tail(30).max()) / close.iloc[-1] < 0.003 else "None",
            "bos": self._find_bos(close, high, low)[-3:],
            "choch": "Likely" if close.diff().tail(5).mean() * close.diff().tail(20).mean() < 0 else "No",
            "daily_bias": daily_bias,
            "displacement": displacement,
            "power_of_3": power_of_3,
            "ote": ote,
            "nwog": nwog,
        }

    def _find_fair_value_gaps(self, df: pd.DataFrame) -> list:
        """
        Fair Value Gap: 3-candle pattern where candle[i+1] leaves an imbalance
        between high[i] and low[i+2] (bullish) or low[i] and high[i+2] (bearish).
        """
        fvgs  = []
        high  = df['high'].values
        low   = df['low'].values
        close = df['close'].values
        n     = len(df)

        for i in range(1, n - 1):
            # Bullish FVG
            if low[i + 1] > high[i - 1]:
                fvgs.append({
                    'type': 'bullish',
                    'start': i,
                    'end': min(i + 10, n - 1),
                    'low': high[i - 1],
                    'high': low[i + 1],
                })

            # Bearish FVG
            if high[i + 1] < low[i - 1]:
                fvgs.append({
                    'type': 'bearish',
                    'start': i,
                    'end': min(i + 10, n - 1),
                    'low': high[i + 1],
                    'high': low[i - 1],
                })

        return fvgs[-6:]

    def _detect_displacement(self, close, high, low) -> str:
        """Detect displacement (large impulse candle)."""
        if len(close) < 5:
            return "Not detected"
        recent_range = (high.tail(20) - low.tail(20)).mean()
        last_candle_range = high.iloc[-1] - low.iloc[-1]
        if last_candle_range > 2.5 * recent_range:
            direction = "Bullish" if close.iloc[-1] > close.iloc[-2] else "Bearish"
            return f"{direction} displacement detected"
        return "No significant displacement"

    def _determine_daily_bias(self, close, high, low) -> str:
        """Determine ICT daily bias."""
        if len(close) < 10:
            return "Neutral"
        open_price = close.iloc[-min(10, len(close))]
        current    = close.iloc[-1]
        session_high = high.tail(10).max()
        session_low  = low.tail(10).min()

        # Premium (above 50% of range) = bearish bias
        range_ = session_high - session_low
        if range_ == 0:
            return "Neutral"
        position = (current - session_low) / range_

        if position > 0.7:   return "Bearish (Premium Zone)"
        elif position < 0.3: return "Bullish (Discount Zone)"
        else:                return "Neutral (Equilibrium)"

    def _power_of_3(self, close) -> str:
        """Classify Power of 3 phase."""
        if len(close) < 30:
            return "Insufficient data"
        segment = close.tail(30)
        vol = segment.std() / segment.mean()

        # Low volatility = accumulation, high = distribution
        if vol < 0.003:
            return "Accumulation (Phase 1)"
        elif vol < 0.007:
            direction = "Up" if segment.iloc[-1] > segment.iloc[0] else "Down"
            return f"Manipulation / Distribution {direction}"
        else:
            direction = "Bullish" if segment.iloc[-1] > segment.iloc[0] else "Bearish"
            return f"{direction} Distribution (Phase 3)"

    def _calculate_ote(self, close, high, low) -> dict:
        """Calculate Optimal Trade Entry (OTE) using Fibonacci 61.8% - 78.6%."""
        recent_high = high.tail(30).max()
        recent_low  = low.tail(30).min()
        range_      = recent_high - recent_low

        ote_618 = recent_high - 0.618 * range_  # bullish entry
        ote_786 = recent_high - 0.786 * range_
        target  = recent_high
        invalid = recent_low

        current = close.iloc[-1]

        if ote_786 <= current <= ote_618:
            status = "Price IN OTE Zone ✓"
        elif current < ote_786:
            status = f"Below OTE – wait for {ote_786:.5f}"
        else:
            status = f"Above OTE – wait for pullback to {ote_618:.5f}"

        return {
            'ote': f"{ote_786:.5f} – {ote_618:.5f}",
            'target': f"{target:.5f}",
            'invalidation': f"{invalid:.5f}",
            'status': status,
        }

    def _find_nwog(self, df: pd.DataFrame) -> str:
        """Detect New Week Opening Gap."""
        try:
            if len(df) < 7:
                return "N/A"
            # Proxy: compare first candle of recent period vs previous
            gap = df['open'].iloc[-5] - df['close'].iloc[-6]
            if abs(gap) / df['close'].iloc[-6] > 0.001:
                direction = "Bullish" if gap > 0 else "Bearish"
                return f"{direction} gap: {gap:.5f}"
            return "No significant gap"
        except:
            return "N/A"


    def _analyze_sk(self):
        close = self.df["close"]
        high = self.df["high"]
        low = self.df["low"]
        seq = "HH/HL" if close.tail(8).is_monotonic_increasing else "LL/LH"
        structure = "Bullish" if close.iloc[-1] > close.rolling(20).mean().iloc[-1] else "Bearish"
        entry_logic = "Wait pullback to MA20 with momentum confirmation"
        phase = self._sk_phase(close)
        signal = self._sk_signal(close, high, low)
        quality = self._sk_quality(close, high, low)
        key_levels = self._sk_key_levels(self.df)
        self.sk_analysis = {
            "sequence": seq,
            "entry_logic": entry_logic,
            "market_structure": structure,
            "phase": phase,
            "signal": signal,
            "quality": quality,
            "key_levels": key_levels,
        }

    def _sk_phase(self, close) -> str:
        """Determine SK system market phase."""
        if len(close) < 40:
            return "Insufficient data"
        
        ema20  = close.ewm(span=20).mean()
        ema50  = close.ewm(span=50).mean()
        
        current = close.iloc[-1]
        e20 = ema20.iloc[-1]
        e50 = ema50.iloc[-1]

        if current > e20 > e50:   return "Phase 1: Uptrend (Long Bias)"
        elif e20 > current > e50: return "Phase 2: Pullback (Watch for entry)"
        elif current > e50 > e20: return "Phase 3: Transition"
        elif current < e20 < e50: return "Phase 4: Downtrend (Short Bias)"
        else:                     return "Transitional Phase"

    def _sk_signal(self, close, high, low) -> str:
        """Generate SK system signal."""
        if len(close) < 20:
            return "N/A"
        
        ema  = close.ewm(span=20).mean()
        rsi  = self._fast_rsi(close)
        current = close.iloc[-1]
        e = ema.iloc[-1]

        if current > e and rsi > 55:
            return "BUY Signal"
        elif current < e and rsi < 45:
            return "SELL Signal"
        elif 45 < rsi < 55:
            return "WAIT – Neutral Zone"
        return "Watch for confirmation"

    def _sk_quality(self, close, high, low) -> str:
        """Assess SK setup quality."""
        rsi = self._fast_rsi(close)
        if   40 < rsi < 60: quality = "A+ Setup (Perfect Range)"
        elif 30 < rsi < 70: quality = "B Setup (Good)"
        else:               quality = "C Setup (Extreme – caution)"
        return quality

    def _sk_key_levels(self, df: pd.DataFrame) -> list:
        """Find SK key levels."""
        close = df['close']
        high  = df['high']
        low   = df['low']
        
        levels = []
        current = close.iloc[-1]

        # Round numbers as psychological levels
        price = current
        magnitude = 10 ** (len(str(int(price))) - 2)
        rounded = round(price / magnitude) * magnitude
        levels.append({'type': 'psychological', 'price': rounded})

        # Recent swing high/low
        levels.append({'type': 'resistance', 'price': high.tail(30).max()})
        levels.append({'type': 'support',    'price': low.tail(30).min()})

        # EMAs as dynamic support/resistance
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema50 = close.ewm(span=50).mean().iloc[-1]
        t20 = 'support' if current > ema20 else 'resistance'
        t50 = 'support' if current > ema50 else 'resistance'
        levels.append({'type': t20, 'price': ema20})
        levels.append({'type': t50, 'price': ema50})

        return levels

    def _fast_rsi(self, close, period=14) -> float:
        """Quick RSI calculation."""
        if len(close) < period + 1:
            return 50
        delta = close.diff()
        gain  = delta.clip(lower=0).ewm(com=period-1, adjust=False).mean()
        loss  = (-delta.clip(upper=0)).ewm(com=period-1, adjust=False).mean()
        rs    = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 1
        return 100 - 100 / (1 + rs)


    def _analyze_ta(self):
        close = self.df["close"]
        high = self.df["high"]
        low = self.df["low"]
        trend = "Bullish" if close.iloc[-1] > close.rolling(20).mean().iloc[-1] else "Bearish"
        self.ta_summary = {
            "trend": trend,
            "support": float(low.tail(30).min()),
            "resistance": float(high.tail(30).max()),
            "moving_average": float(close.rolling(20).mean().iloc[-1]),
        }
