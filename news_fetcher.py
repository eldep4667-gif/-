"""
NEXUS Trading Platform - News and Calendar Fetcher
Fetches real market news plus upcoming macro events relevant to the selected instrument.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import requests


class NewsFetcher:
    """Fetch real market news and economic events related to the selected symbol."""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    SYMBOL_CONFIG = {
        "EUR/USD": {
            "queries": ["EUR USD forex", "euro dollar ECB Federal Reserve", "EURUSD Reuters"],
            "required_terms": ["euro", "eur", "dollar", "usd", "ecb", "federal reserve"],
            "quote_terms": ["dollar", "usd", "fed", "federal reserve"],
            "base_terms": ["euro", "eur", "ecb", "eurozone"],
            "countries": ["Euro Area", "United States"],
            "currencies": ["EUR", "USD"],
        },
        "GBP/USD": {
            "queries": ["GBP USD forex", "pound sterling dollar Bank of England Federal Reserve", "GBPUSD Reuters"],
            "required_terms": ["pound", "sterling", "gbp", "dollar", "usd", "bank of england", "fed"],
            "quote_terms": ["dollar", "usd", "fed", "federal reserve"],
            "base_terms": ["pound", "sterling", "gbp", "bank of england", "boe"],
            "countries": ["United Kingdom", "United States"],
            "currencies": ["GBP", "USD"],
        },
        "USD/JPY": {
            "queries": ["USD JPY forex", "dollar yen Bank of Japan Federal Reserve", "USDJPY Reuters"],
            "required_terms": ["yen", "jpy", "dollar", "usd", "bank of japan", "boj", "fed"],
            "quote_terms": ["yen", "jpy", "bank of japan", "boj"],
            "base_terms": ["dollar", "usd", "fed", "federal reserve"],
            "countries": ["Japan", "United States"],
            "currencies": ["JPY", "USD"],
        },
        "BTC/USDT": {
            "queries": ["bitcoin crypto markets", "BTC USDT bitcoin ETF regulation", "bitcoin Reuters"],
            "required_terms": ["bitcoin", "btc", "crypto", "cryptocurrency"],
            "quote_terms": ["tether", "usdt", "stablecoin", "dollar"],
            "base_terms": ["bitcoin", "btc", "crypto", "etf", "miners"],
            "countries": ["United States"],
            "currencies": ["USD"],
        },
        "ETH/USDT": {
            "queries": ["ethereum crypto markets", "ETH USDT ethereum ETF regulation", "ethereum Reuters"],
            "required_terms": ["ethereum", "eth", "crypto", "cryptocurrency"],
            "quote_terms": ["tether", "usdt", "stablecoin", "dollar"],
            "base_terms": ["ethereum", "eth", "ether", "staking", "defi"],
            "countries": ["United States"],
            "currencies": ["USD"],
        },
        "AAPL": {
            "queries": ["Apple stock", "AAPL earnings iPhone supply chain", "Apple Reuters"],
            "required_terms": ["apple", "aapl", "iphone", "tim cook"],
            "quote_terms": ["nasdaq", "stocks", "equities"],
            "base_terms": ["apple", "aapl", "iphone", "services"],
            "countries": ["United States"],
            "currencies": ["USD"],
        },
        "TSLA": {
            "queries": ["Tesla stock", "TSLA deliveries margins EV", "Tesla Reuters"],
            "required_terms": ["tesla", "tsla", "elon musk", "electric vehicle", "ev"],
            "quote_terms": ["nasdaq", "stocks", "equities"],
            "base_terms": ["tesla", "tsla", "elon musk", "ev", "deliveries"],
            "countries": ["United States"],
            "currencies": ["USD"],
        },
    }

    POSITIVE_WORDS = [
        "surge", "rally", "gain", "rise", "bullish", "growth", "strong",
        "beat", "record", "breakout", "approval", "expansion", "optimistic",
    ]
    NEGATIVE_WORDS = [
        "fall", "drop", "decline", "crash", "bearish", "loss", "weak", "miss",
        "sell-off", "plunge", "warning", "downgrade", "lawsuit", "recession",
    ]
    HIGH_IMPACT_WORDS = [
        "cpi", "inflation", "interest rate", "federal reserve", "fed", "ecb",
        "bank of england", "bank of japan", "payrolls", "nfp", "earnings",
        "etf", "regulation", "tariff", "gdp", "ppi", "fomc",
    ]
    EVENT_IMPACT_KEYWORDS = {
        "Interest Rate": 3,
        "Inflation Rate": 3,
        "CPI": 3,
        "Core Inflation Rate": 3,
        "Non Farm Payrolls": 3,
        "GDP Growth Rate": 3,
        "Retail Sales": 2,
        "PMI": 2,
        "Unemployment Rate": 2,
        "Earnings": 2,
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def get_news(self, symbol: str) -> list[dict]:
        config = self.SYMBOL_CONFIG.get(symbol, {})
        queries = config.get("queries", [f"{symbol} markets"])
        articles: list[dict] = []

        gnews_key = self._get_secret("GNEWS_API_KEY")
        newsapi_key = self._get_secret("NEWSAPI_KEY")
        if gnews_key:
            articles.extend(self._fetch_gnews(queries, gnews_key))
        if newsapi_key and len(articles) < 6:
            articles.extend(self._fetch_newsapi(queries, newsapi_key))

        if len(articles) < 6:
            articles.extend(self._fetch_google_news_rss(queries))
        if len(articles) < 6:
            articles.extend(self._fetch_topic_rss(symbol))

        return self._dedupe_and_rank(symbol, articles)[:10]

    def get_calendar_events(self, symbol: str) -> list[dict]:
        config = self.SYMBOL_CONFIG.get(symbol, {})
        countries = config.get("countries", [])
        if not countries:
            return []

        api_key = self._get_secret("TRADING_ECONOMICS_API_KEY") or "guest:guest"
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=7)
        start_str = now.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        events: list[dict] = []
        try:
            response = self.session.get(
                f"https://api.tradingeconomics.com/calendar?c={api_key}&f=json&start={start_str}&end={end_str}",
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        for raw in payload:
            country = raw.get("Country") or raw.get("country") or ""
            if country not in countries:
                continue

            event_time = self._parse_datetime(raw.get("Date") or raw.get("date"))
            if not event_time or event_time < now:
                continue

            event_name = raw.get("Event") or raw.get("event") or raw.get("Category") or "Economic Event"
            impact_score = self._calendar_impact_score(raw)
            currency = raw.get("Currency") or raw.get("currency") or ""
            event = {
                "title": event_name,
                "country": country,
                "currency": currency,
                "datetime": event_time,
                "time_label": event_time.strftime("%d %b · %H:%M UTC"),
                "countdown": self._countdown(event_time, now),
                "impact_score": impact_score,
                "impact_label": self._impact_label(impact_score),
                "actual": self._clean_value(raw.get("Actual") or raw.get("actual")),
                "forecast": self._clean_value(raw.get("Forecast") or raw.get("forecast")),
                "previous": self._clean_value(raw.get("Previous") or raw.get("previous")),
                "source": "TradingEconomics",
                "effect_on_symbol": self._event_effect(symbol, country, currency, event_name, impact_score),
            }
            events.append(event)

        events.sort(key=lambda item: (item["datetime"], -item["impact_score"]))
        return events[:12]

    def summarize_news(self, symbol: str, news_items: list[dict]) -> dict:
        if not news_items:
            return {
                "sentiment": "neutral",
                "score": 0.0,
                "headline": "No reliable live news available right now.",
                "impact_label": "Unknown",
            }

        score = 0.0
        high_impact_count = 0
        for item in news_items[:5]:
            sentiment = item.get("sentiment", "neutral")
            impact = item.get("impact_score", 0)
            if sentiment == "positive":
                score += 1.0 + impact * 0.15
            elif sentiment == "negative":
                score -= 1.0 + impact * 0.15
            if impact >= 2:
                high_impact_count += 1

        sentiment = "positive" if score > 0.75 else "negative" if score < -0.75 else "neutral"
        impact_label = "High" if high_impact_count >= 2 else "Medium" if high_impact_count == 1 else "Low"
        return {
            "sentiment": sentiment,
            "score": round(score, 2),
            "headline": news_items[0].get("title", "Latest market news loaded."),
            "impact_label": impact_label,
            "article_count": len(news_items),
            "symbol": symbol,
        }

    def _fetch_gnews(self, queries: list[str], api_key: str) -> list[dict]:
        items: list[dict] = []
        for query in queries[:2]:
            try:
                response = self.session.get(
                    "https://gnews.io/api/v4/search",
                    params={"q": query, "lang": "en", "max": 6, "token": api_key},
                    timeout=8,
                )
                response.raise_for_status()
                data = response.json()
                for article in data.get("articles", []):
                    items.append(self._article_payload(
                        title=article.get("title", ""),
                        description=article.get("description", ""),
                        published_raw=article.get("publishedAt"),
                        source=article.get("source", {}).get("name", "GNews"),
                        url=article.get("url", ""),
                    ))
            except Exception:
                continue
        return items

    def _fetch_newsapi(self, queries: list[str], api_key: str) -> list[dict]:
        items: list[dict] = []
        for query in queries[:2]:
            try:
                response = self.session.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "language": "en",
                        "pageSize": 6,
                        "sortBy": "publishedAt",
                        "apiKey": api_key,
                    },
                    timeout=8,
                )
                response.raise_for_status()
                data = response.json()
                for article in data.get("articles", []):
                    items.append(self._article_payload(
                        title=article.get("title", ""),
                        description=article.get("description", ""),
                        published_raw=article.get("publishedAt"),
                        source=article.get("source", {}).get("name", "NewsAPI"),
                        url=article.get("url", ""),
                    ))
            except Exception:
                continue
        return items

    def _fetch_google_news_rss(self, queries: list[str]) -> list[dict]:
        items: list[dict] = []
        for query in queries[:3]:
            try:
                url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
                response = self.session.get(url, timeout=8)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                for item in root.findall(".//item")[:6]:
                    title = self._clean_text(item.findtext("title", ""))
                    description = self._clean_text(item.findtext("description", ""))
                    items.append(self._article_payload(
                        title=title,
                        description=description,
                        published_raw=item.findtext("pubDate", ""),
                        source=self._extract_source(title),
                        url=item.findtext("link", ""),
                    ))
            except Exception:
                continue
        return items

    def _fetch_topic_rss(self, symbol: str) -> list[dict]:
        topic_queries = {
            "BTC/USDT": "site:coindesk.com bitcoin OR btc",
            "ETH/USDT": "site:coindesk.com ethereum OR eth",
            "AAPL": "site:finance.yahoo.com Apple stock",
            "TSLA": "site:finance.yahoo.com Tesla stock",
        }
        query = topic_queries.get(symbol)
        return self._fetch_google_news_rss([query]) if query else []

    def _dedupe_and_rank(self, symbol: str, articles: list[dict]) -> list[dict]:
        config = self.SYMBOL_CONFIG.get(symbol, {})
        required_terms = config.get("required_terms", [])
        quote_terms = config.get("quote_terms", [])
        base_terms = config.get("base_terms", [])

        ranked: list[dict] = []
        seen = set()
        for article in articles:
            title = article.get("title", "").strip()
            description = article.get("description", "").strip()
            if not title:
                continue

            slug = re.sub(r"[^a-z0-9]+", "", title.lower())
            if slug in seen:
                continue
            seen.add(slug)

            text = f"{title} {description}".lower()
            relevance = self._relevance_score(text, required_terms, base_terms, quote_terms)
            if relevance < 1:
                continue

            sentiment = self._analyze_sentiment(text)
            impact_score = self._impact_score(text)
            ranked.append({
                **article,
                "sentiment": sentiment,
                "impact_score": impact_score,
                "impact_label": self._impact_label(impact_score),
                "relevance_score": relevance,
            })

        ranked.sort(
            key=lambda item: (item.get("impact_score", 0), item.get("relevance_score", 0), item.get("published_sort", "")),
            reverse=True,
        )
        return ranked

    def _article_payload(self, title: str, description: str, published_raw: str | None, source: str, url: str) -> dict:
        return {
            "title": title,
            "description": description,
            "published": self._format_time(published_raw),
            "published_raw": published_raw,
            "published_sort": self._sortable_date(published_raw),
            "source": source,
            "url": url,
        }

    def _relevance_score(self, text: str, required_terms: list[str], base_terms: list[str], quote_terms: list[str]) -> int:
        score = 0
        score += sum(1 for term in required_terms if term.lower() in text)
        score += sum(2 for term in base_terms if term.lower() in text)
        score += sum(1 for term in quote_terms if term.lower() in text)
        return score

    def _impact_score(self, text: str) -> int:
        impact = sum(1 for word in self.HIGH_IMPACT_WORDS if word in text)
        if any(word in text for word in ["breaking", "live", "urgent", "just in"]):
            impact += 1
        return min(3, impact)

    def _calendar_impact_score(self, raw: dict) -> int:
        importance = raw.get("Importance") or raw.get("importance") or 1
        category = str(raw.get("Category") or raw.get("category") or raw.get("Event") or "")
        keyword_score = 0
        for key, value in self.EVENT_IMPACT_KEYWORDS.items():
            if key.lower() in category.lower():
                keyword_score = max(keyword_score, value)
        try:
            importance = int(float(importance))
        except Exception:
            importance = 1
        return max(min(max(importance, keyword_score), 3), 1)

    def _impact_label(self, score: int) -> str:
        if score >= 3:
            return "High"
        if score == 2:
            return "Medium"
        return "Low"

    def _event_effect(self, symbol: str, country: str, currency: str, event_name: str, impact_score: int) -> str:
        pair = self.SYMBOL_CONFIG.get(symbol, {})
        currencies = pair.get("currencies", [])
        title = event_name.lower()

        if symbol in {"BTC/USDT", "ETH/USDT"} and country == "United States":
            return "High-impact US macro news can move crypto liquidity and risk sentiment."

        if currency in currencies:
            if any(term in title for term in ["interest", "cpi", "inflation", "payroll", "fomc", "rate"]):
                return f"This is a {self._impact_label(impact_score).lower()}-impact macro release directly tied to {currency}, so volatility can expand fast."
            return f"This release is directly relevant to {currency} and can shift short-term bias on {symbol}."

        return f"This release matters indirectly to {symbol}, mainly through broad risk sentiment."

    def _analyze_sentiment(self, text: str) -> str:
        pos_count = sum(1 for word in self.POSITIVE_WORDS if word in text)
        neg_count = sum(1 for word in self.NEGATIVE_WORDS if word in text)
        if pos_count > neg_count:
            return "positive"
        if neg_count > pos_count:
            return "negative"
        return "neutral"

    def _extract_source(self, title: str) -> str:
        parts = [part.strip() for part in title.split(" - ") if part.strip()]
        return parts[-1][:48] if len(parts) >= 2 else "Google News"

    def _get_secret(self, key: str) -> str | None:
        try:
            import streamlit as st

            if key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass
        return os.getenv(key)

    def _clean_text(self, value: str) -> str:
        cleaned = re.sub(r"<.*?>", " ", value or "")
        return re.sub(r"\s+", " ", cleaned).strip()

    def _clean_value(self, value) -> str:
        if value in (None, "", "null"):
            return "N/A"
        return str(value)

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            try:
                dt = parsedate_to_datetime(str(value))
            except Exception:
                return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _countdown(self, event_time: datetime, now: datetime) -> str:
        delta = event_time - now
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return "Released"
        hours, rem = divmod(total_seconds, 3600)
        minutes = rem // 60
        days, hours = divmod(hours, 24)
        if days > 0:
            return f"in {days}d {hours}h"
        if hours > 0:
            return f"in {hours}h {minutes}m"
        return f"in {minutes}m"

    def _format_time(self, value: str | None) -> str:
        dt = self._parse_datetime(value)
        return dt.strftime("%d %b · %H:%M UTC") if dt else "Recent"

    def _sortable_date(self, value: str | None) -> str:
        dt = self._parse_datetime(value)
        return dt.isoformat() if dt else ""
