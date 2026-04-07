from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf
from flask import Flask, jsonify, render_template, request

from modules.ai_signals import AISignalEngine
from modules.news_fetcher import NewsFetcher
from modules.pattern_detection import PatternDetector
from modules.technical_analysis import TechnicalAnalyzer
from modules.trading_schools import TradingSchoolsAnalyzer

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".cache" / "yfinance"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
try:
    yf.set_tz_cache_location(str(CACHE_DIR))
except Exception:
    pass

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))
news_fetcher = NewsFetcher()

SYMBOLS = {
    "EUR/USD": "FX:EURUSD",
    "GBP/USD": "FX:GBPUSD",
    "USD/JPY": "FX:USDJPY",
    "BTC/USDT": "BINANCE:BTCUSDT",
    "ETH/USDT": "BINANCE:ETHUSDT",
    "AAPL": "NASDAQ:AAPL",
    "TSLA": "NASDAQ:TSLA",
}
YF_SYMBOLS = {
    "FX:EURUSD": "EURUSD=X",
    "FX:GBPUSD": "GBPUSD=X",
    "FX:USDJPY": "JPY=X",
    "BINANCE:BTCUSDT": "BTC-USD",
    "BINANCE:ETHUSDT": "ETH-USD",
    "NASDAQ:AAPL": "AAPL",
    "NASDAQ:TSLA": "TSLA",
}
TV_INTERVALS = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1D": "D"}
YF_INTERVALS = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "1h", "1D": "1d"}
MODES = {
    "SMART": {"label": "Smart AI", "accent": "#57d8ff"},
    "SMC": {"label": "SMC", "accent": "#7c92ff"},
    "ICT": {"label": "ICT", "accent": "#c084fc"},
    "SK": {"label": "SK", "accent": "#ffb86c"},
}


def load_ohlcv(symbol: str, interval: str) -> pd.DataFrame:
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval=interval)
        if df.empty:
            return pd.DataFrame()
        df.columns = [col.lower() for col in df.columns]
        return df[["open", "high", "low", "close", "volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def fetch_market_intel(symbol: str) -> tuple[list[dict], dict, list[dict]]:
    news_items = news_fetcher.get_news(symbol)
    summary = news_fetcher.summarize_news(symbol, news_items)
    events = news_fetcher.get_calendar_events(symbol)
    return news_items, summary, events


def analyze_market(pair_name: str, tf_name: str, mode: str) -> tuple[dict, dict]:
    symbol_tv = SYMBOLS[pair_name]
    symbol_yf = YF_SYMBOLS[symbol_tv]
    market = load_ohlcv(symbol_yf, YF_INTERVALS[tf_name])
    if market.empty:
        raise ValueError("Live market data is temporarily unavailable for this symbol or timeframe.")

    news_items, news_summary, events = fetch_market_intel(pair_name)
    technical = TechnicalAnalyzer(market)
    patterns = PatternDetector(market)
    schools = TradingSchoolsAnalyzer(market)
    engine = AISignalEngine(market, technical, patterns, schools, news_summary)
    signal = engine.generate_signal(mode=mode)

    details = {
        "technical_snapshot": technical.get_indicators_snapshot(),
        "support_levels": technical.support_levels,
        "resistance_levels": technical.resistance_levels,
        "trendline": technical.trendline,
        "patterns": patterns.detected_patterns,
        "schools": {
            "smc": schools.smc_analysis,
            "ict": schools.ict_analysis,
            "sk": schools.sk_analysis,
            "ta": schools.ta_summary,
        },
        "news_summary": news_summary,
        "calendar_events": events[:6],
        "news_items": news_items[:6],
    }
    return signal, details


def jsonify_safe(value):
    if isinstance(value, dict):
        return {str(k): jsonify_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [jsonify_safe(v) for v in value]
    if isinstance(value, tuple):
        return [jsonify_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


@app.route("/")
def index():
    return render_template(
        "index.html",
        symbols=list(SYMBOLS.keys()),
        intervals=list(TV_INTERVALS.keys()),
        modes=MODES,
        default_symbol="EUR/USD",
        default_interval="1h",
        generated_at=datetime.now(timezone.utc).strftime("%A, %d %B %Y · %H:%M UTC"),
    )


@app.get("/api/bootstrap")
def bootstrap():
    pair_name = request.args.get("symbol", "EUR/USD")
    tf_name = request.args.get("timeframe", "1h")
    mode = request.args.get("mode", "SMART")
    news_items, news_summary, events = fetch_market_intel(pair_name)
    return jsonify(
        {
            "symbols": list(SYMBOLS.keys()),
            "intervals": list(TV_INTERVALS.keys()),
            "modes": MODES,
            "selected_symbol": pair_name,
            "selected_timeframe": tf_name,
            "selected_mode": mode,
            "symbol_tv": SYMBOLS[pair_name],
            "news": jsonify_safe(news_items),
            "news_summary": jsonify_safe(news_summary),
            "events": jsonify_safe(events),
        }
    )


@app.get("/api/market-intel")
def market_intel():
    pair_name = request.args.get("symbol", "EUR/USD")
    news_items, news_summary, events = fetch_market_intel(pair_name)
    return jsonify(
        {
            "symbol": pair_name,
            "symbol_tv": SYMBOLS[pair_name],
            "news": jsonify_safe(news_items),
            "news_summary": jsonify_safe(news_summary),
            "events": jsonify_safe(events),
        }
    )


@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    pair_name = payload.get("symbol", "EUR/USD")
    tf_name = payload.get("timeframe", "1h")
    mode = payload.get("mode", "SMART")
    try:
        signal, details = analyze_market(pair_name, tf_name, mode)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400

    return jsonify(
        {
            "ok": True,
            "symbol": pair_name,
            "symbol_tv": SYMBOLS[pair_name],
            "timeframe": tf_name,
            "mode": mode,
            "result": jsonify_safe(signal),
            "details": jsonify_safe(details),
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
