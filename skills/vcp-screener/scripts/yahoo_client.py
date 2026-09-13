#!/usr/bin/env python3
"""Yahoo Finance chart-API client — free, keyless alternative to FMPClient.

Added because a free-tier FMP key only has data access to a small curated
ticker list (confirmed: AAPL MSFT NVDA AMZN META GOOGL TSLA COST WMT), not
"all stocks except ETFs" as first assumed. Ordinary S&P 500 names (MMM, APD,
AVGO, ...) and ETFs (HYG) are blocked on that tier for both quotes and
historical data. Yahoo's public chart endpoint (`/v8/finance/chart/{symbol}`)
was verified working for all of MMM, HYG, SPY, and BRK-B with no API key.

Duck-types the same public interface as ``FMPClient`` (``get_historical_prices``,
``get_quote``, ``get_batch_quotes``, ``get_batch_historical``,
``get_sp500_constituents``, ``get_api_stats``) so ``screen_vcp.py`` can swap
between clients via ``--data-source``.

Design choice: there is no separate "quote" endpoint here. A quote dict
(price / yearHigh / yearLow / avgVolume / marketCap) is synthesized from the
same historical-bars response used for pattern detection — one HTTP fetch
serves both Phase 1 pre-filtering and Phase 2 trend-template analysis, so
this is also a genuine efficiency improvement over FMP's original two-calls-
per-symbol design, not just a stopgap.

Known gaps vs. FMPClient:
- No real-time intraday quote; ``price`` is the latest daily close.
- ``marketCap`` is not available from this endpoint and is always 0
  (historical share count isn't retrievable from OHLCV) — same limitation
  the historical scanner already documents for FMP's own historical mode.
  It's a display-only field; nothing in the scoring/filtering logic reads it.
- Sector/subSector metadata isn't provided; unaffected, since
  ``get_sp500_constituents`` still uses the existing free CSV fallback for
  that.
"""

from __future__ import annotations

import csv
import io
import sys
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def _build_quote_from_bars(
    historical: list[dict],
    meta: Optional[dict] = None,
    year_window_bars: int = 252,
    vol_window_bars: int = 50,
) -> dict:
    """Synthesize a quote dict (price/yearHigh/yearLow/avgVolume/marketCap)
    from most-recent-first OHLCV bars, preferring Yahoo's own 52-week
    high/low from ``meta`` when available (more accurate than a 252-bar
    approximation, since it tracks calendar weeks, not trading-day counts).
    """
    if not historical:
        return {"price": 0, "yearHigh": 0, "yearLow": 0, "avgVolume": 0, "marketCap": 0}

    price = historical[0].get("close", 0) or 0
    meta = meta or {}

    year_high = meta.get("fiftyTwoWeekHigh")
    year_low = meta.get("fiftyTwoWeekLow")
    if year_high is None or year_low is None:
        window = historical[:year_window_bars]
        highs = [d.get("high", 0) for d in window if d.get("high")]
        lows = [d.get("low", 0) for d in window if d.get("low")]
        year_high = max(highs) if highs else 0
        year_low = min(lows) if lows else 0

    vol_window = historical[:vol_window_bars]
    volumes = [d.get("volume", 0) or 0 for d in vol_window]
    avg_volume = int(sum(volumes) / len(volumes)) if volumes else 0

    return {
        "price": price,
        "yearHigh": year_high,
        "yearLow": year_low,
        "avgVolume": avg_volume,
        "marketCap": 0,  # not derivable from OHLCV; display-only field elsewhere.
    }


class YahooClient:
    """Free, keyless historical/quote client backed by Yahoo's chart API."""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
    RATE_LIMIT_DELAY = 0.3  # be a polite, unauthenticated citizen

    _CONSTITUENTS_CSV_URL = (
        "https://raw.githubusercontent.com/datasets/"
        "s-and-p-500-companies/main/data/constituents.csv"
    )

    def __init__(self, api_key: Optional[str] = None):
        # api_key accepted only so this class is drop-in compatible with
        # FMPClient's constructor signature; Yahoo's public chart endpoint
        # needs no key and the argument is ignored.
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (solo-trader-os vcp-screener)"})
        self.cache: dict[str, dict] = {}
        self.last_call_time = 0.0
        self.api_calls_made = 0
        self.rate_limit_reached = False  # kept for interface parity; unused (no known daily cap)
        self._last_error: Optional[str] = None

    def _rate_limited_fetch(self, symbol: str, days: int) -> Optional[dict]:
        cache_key = f"hist_{symbol}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        elapsed = time.time() - self.last_call_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)

        now = int(time.time())
        # *2 calendar-day buffer (same ratio _fmp_compat.py uses) plus a
        # week of slack for holidays/weekends at the requested-days boundary.
        period1 = now - int(days * 2 * 86400) - 7 * 86400
        url = f"{self.BASE_URL}/{symbol}"
        params = {"period1": period1, "period2": now, "interval": "1d"}

        try:
            resp = self.session.get(url, params=params, timeout=30)
            self.last_call_time = time.time()
            self.api_calls_made += 1
        except requests.exceptions.RequestException as exc:
            self._last_error = f"request exception: {exc}"
            return None

        if resp.status_code != 200:
            self._last_error = f"HTTP {resp.status_code}"
            return None

        try:
            payload = resp.json()
            result = payload["chart"]["result"][0]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            self._last_error = f"unexpected response shape: {exc}"
            return None

        timestamps = result.get("timestamp") or []
        quote_block = (result.get("indicators", {}).get("quote") or [{}])[0]
        opens = quote_block.get("open") or []
        highs = quote_block.get("high") or []
        lows = quote_block.get("low") or []
        closes = quote_block.get("close") or []
        volumes = quote_block.get("volume") or []

        bars = []
        for i, ts in enumerate(timestamps):
            close = closes[i] if i < len(closes) else None
            if close is None:
                continue  # Yahoo pads non-trading timestamps with nulls
            bars.append(
                {
                    "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "open": opens[i] if i < len(opens) else close,
                    "high": highs[i] if i < len(highs) else close,
                    "low": lows[i] if i < len(lows) else close,
                    "close": close,
                    "volume": volumes[i] if i < len(volumes) else 0,
                }
            )

        bars.reverse()  # Yahoo returns oldest-first; our contract is most-recent-first
        if days:
            bars = bars[:days]

        out = {"symbol": symbol, "historical": bars, "_meta": result.get("meta", {})}
        self.cache[cache_key] = out
        return out

    # ------------------------------------------------------------------ #
    # FMPClient-compatible public interface
    # ------------------------------------------------------------------ #
    def get_historical_prices(self, symbol: str, days: int = 365) -> Optional[dict]:
        """Fetch historical daily OHLCV data. Same return shape as
        ``FMPClient.get_historical_prices``: ``{"symbol", "historical": [...]}``.
        """
        data = self._rate_limited_fetch(symbol, days)
        if data is None or not data.get("historical"):
            return None
        # Drop the internal _meta key before handing back to callers that
        # don't expect it (keeps the contract identical to FMPClient).
        return {"symbol": data["symbol"], "historical": data["historical"]}

    def get_quote(self, symbols: str) -> Optional[list[dict]]:
        """Fetch one synthesized quote per comma-separated symbol."""
        results = []
        for sym in symbols.split(","):
            sym = sym.strip()
            if not sym:
                continue
            data = self._rate_limited_fetch(sym, 260)
            if data is None or not data.get("historical"):
                continue
            quote = _build_quote_from_bars(data["historical"], meta=data.get("_meta"))
            quote["symbol"] = sym
            results.append(quote)
        return results or None

    def get_batch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Fetch quotes for a list of symbols. No real batching exists on
        this free endpoint — one fetch per symbol, same as ``get_quote``
        looped. Kept as a separate method for interface parity with
        FMPClient and because the 260-day fetch here is cached and reused
        by Phase 2's historical request for the same symbol/day-count.
        """
        results: dict[str, dict] = {}
        for sym in symbols:
            quotes = self.get_quote(sym)
            if quotes:
                for q in quotes:
                    results[q["symbol"]] = q
        return results

    def get_batch_historical(self, symbols: list[str], days: int = 260) -> dict[str, list[dict]]:
        """Fetch historical prices for multiple symbols."""
        results = {}
        for symbol in symbols:
            data = self.get_historical_prices(symbol, days=days)
            if data and "historical" in data:
                results[symbol] = data["historical"]
        return results

    def get_sp500_constituents(self) -> Optional[list[dict]]:
        """Fetch the current S&P 500 constituent list from the free public
        dataset (identical fallback to ``FMPClient``'s — no Yahoo call
        needed; this data doesn't come from Yahoo at all).
        """
        cache_key = "sp500_constituents"
        if cache_key in self.cache:
            return self.cache[cache_key]
        try:
            resp = requests.get(self._CONSTITUENTS_CSV_URL, timeout=30)
            if resp.status_code != 200:
                print(
                    f"ERROR: constituents CSV fallback failed: {resp.status_code}",
                    file=sys.stderr,
                )
                return None
            data = [
                {
                    "symbol": row["Symbol"].replace(".", "-"),
                    "name": row["Security"],
                    "sector": row["GICS Sector"],
                    "subSector": row["GICS Sub-Industry"],
                }
                for row in csv.DictReader(io.StringIO(resp.text))
                if row.get("Symbol")
            ]
        except (requests.exceptions.RequestException, csv.Error, KeyError) as exc:
            print(f"ERROR: constituents CSV fallback failed: {exc}", file=sys.stderr)
            return None
        if data:
            self.cache[cache_key] = data
        return data or None

    def get_api_stats(self) -> dict:
        return {
            "cache_entries": len(self.cache),
            "api_calls_made": self.api_calls_made,
            "rate_limit_reached": self.rate_limit_reached,
        }
