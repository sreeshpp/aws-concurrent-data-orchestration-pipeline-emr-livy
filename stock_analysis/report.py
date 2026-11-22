"""Build a five-pillar equity note from inputs the user actually provided.

No market-data vendor is called. A figure that needs a feed is `unavailable`.
Nothing in this module estimates a missing number or invents a calendar date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

US_EXCHANGES = ("NYSE", "NASDAQ", "NYSE American", "NYSE Arca", "Cboe")
INDIA_EXCHANGES = ("NSE", "BSE")

EXCHANGES: dict[str, dict[str, str]] = {
    "NYSE": {"group": "us", "currency": "USD"},
    "NASDAQ": {"group": "us", "currency": "USD"},
    "NYSE American": {"group": "us", "currency": "USD"},
    "NYSE Arca": {"group": "us", "currency": "USD"},
    "Cboe": {"group": "us", "currency": "USD"},
    "NSE": {"group": "india", "currency": "INR"},
    "BSE": {"group": "india", "currency": "INR"},
}

HORIZONS: dict[str, str] = {
    "swing": "Short-term swing trade (1–4 weeks)",
    "medium": "Medium-term (3–12 months)",
    "long": "Long-term (1–5+ years)",
}

RISKS: dict[str, str] = {
    "conservative": "Conservative",
    "moderate": "Moderate",
    "aggressive": "Aggressive",
}

DISCLAIMER = (
    "This note is not personalized financial advice. It does not say buy, "
    "sell, or hold, and it does not guarantee an outcome. Horizon and risk "
    "tolerance change which evidence would be weighted. They do not change "
    "that language."
)

DATA_QUALITY = (
    {
        "title": "Reporting lag",
        "text": (
            "13F positions are as of quarter-end and can be filed up to 45 days "
            "later. Indian shareholding patterns are quarterly. US short interest "
            "is published on a twice-monthly cycle. None of these are the live book."
        ),
    },
    {
        "title": "Later revisions",
        "text": (
            "Filings and exchange files are amended. A sourced figure needs the "
            "retrieval date as well as the as-of date. A later amendment replaces "
            "the earlier figure. No source was retrieved for this note."
        ),
    },
    {
        "title": "Corporate-action adjustments",
        "text": (
            "Prices and share counts have to say whether they are split- and "
            "dividend-adjusted. An unadjusted print must not be compared across "
            "a split, bonus, or dividend. No adjusted series was supplied."
        ),
    },
    {
        "title": "Volume distortion",
        "text": (
            "Block and bulk prints, auction uncrosses, index rebalances, and "
            "off-market transfers can dominate a session. End-of-day volume does "
            "not reveal spoofing. One high-volume day is not accumulation."
        ),
    },
)

FRESHNESS_WINDOWS = (
    {
        "series": "Last trade and OHLC",
        "window": "Stale if older than the latest completed regular session.",
    },
    {
        "series": "Volume and 20-day or 50-day average",
        "window": (
            "Inherits the volume series, and must be adjusted for any corporate "
            "action inside the window."
        ),
    },
    {
        "series": "13F (US listings only)",
        "window": (
            "Lagged by construction (quarter-end, filing up to 45 days later). "
            "Also stale if the quarter or the filing date is missing or is not "
            "the latest filing available on the run date."
        ),
    },
    {
        "series": "Form 4 open-market trades (US listings only)",
        "window": (
            "Recent means a transaction date inside 90 days after excluding tax "
            "withholding and 10b5-1 plans. Stale if the newest filing is older "
            "than that, or if the source did not apply the filter."
        ),
    },
    {
        "series": "US short interest and days-to-cover",
        "window": (
            "Stale if older than the latest twice-monthly publication. "
            "Days-to-cover also needs average volume from a source."
        ),
    },
    {
        "series": "India shareholding and stock-level FII/DII",
        "window": (
            "Stale if older than the latest quarter's shareholding pattern. "
            "Market-wide daily FII/DII totals are not this stock's holding change."
        ),
    },
    {
        "series": "Bulk and block deals",
        "window": "A recent read is stale after 10 trading days.",
    },
    {
        "series": "Exchange short or SLB",
        "window": (
            "Only where that venue publishes the series. Stale past that venue's "
            "latest cycle. If the venue did not return a file, the value is "
            "unavailable, not zero."
        ),
    },
)

HORIZON_WEIGHT = {
    "swing": (
        "Short-term swing (1–4 weeks) would weight the daily and weekly trend, "
        "up-day versus down-day volume, short interest or SLB where a venue "
        "publishes it, and catalysts inside the next month. Fundamentals stay "
        "as context."
    ),
    "medium": (
        "Medium-term (3–12 months) would weight fundamentals and valuation "
        "together with the trend and this venue's flow series across the window. "
        "A single session does not carry the note."
    ),
    "long": (
        "Long-term (1–5+ years) would weight revenue, profitability or cash "
        "burn, leverage, and valuation versus peers. Short-term price levels "
        "and flow are secondary context."
    ),
}

RISK_WEIGHT = {
    "conservative": (
        "Conservative risk tolerance lets missing series and leverage gaps "
        "weigh more in the risk checklist."
    ),
    "moderate": (
        "Moderate risk tolerance weighs the five pillars together."
    ),
    "aggressive": (
        "Aggressive risk tolerance would weight trend confirmation and dated "
        "catalysts more, once those series exist."
    ),
}

WEIGHT_CLOSE = (
    "None of these settings produce a buy, sell, or hold line, and none of "
    "them fill in a missing number."
)

NOT_CONNECTED_FRESHNESS = (
    "No as-of date, so this figure is stale against its window."
)


class ReportError(ValueError):
    """The form inputs cannot build a note."""


def build_report(payload: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Return the five-pillar note for a validated form payload."""
    ticker = _ticker(payload.get("ticker"))
    exchange = _choice(payload.get("exchange"), EXCHANGES, "an exchange")
    horizon = _choice(payload.get("horizon"), HORIZONS, "a horizon")
    risk = _choice(payload.get("risk_tolerance"), RISKS, "a risk tolerance")
    last_price = _last_price(payload.get("last_price"))
    venue = EXCHANGES[exchange]
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    opening = (
        f"This note asks whether buying versus selling pressure confirms the "
        f"price trend for {ticker} on {exchange}. It does not recommend a "
        f"purchase or a sale."
    )
    weighting = f"{HORIZON_WEIGHT[horizon]} {RISK_WEIGHT[risk]} {WEIGHT_CLOSE}"

    pillars = [
        _fundamentals(),
        _trend(last_price, venue["currency"]),
        _pressure(venue["group"]),
        _alignment(venue["group"]),
        _summary(venue["group"], last_price, venue["currency"]),
    ]

    return {
        "opening": opening,
        "disclaimer": DISCLAIMER,
        "weighting": weighting,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_note": "Not a market as-of.",
        "sources_called": [],
        "identity": {
            "ticker": ticker,
            "exchange": exchange,
            "venue_group": venue["group"],
            "currency": venue["currency"],
            "horizon": horizon,
            "horizon_label": HORIZONS[horizon],
            "risk_tolerance": risk,
            "risk_label": RISKS[risk],
        },
        "data_quality": list(DATA_QUALITY),
        "freshness_windows": list(FRESHNESS_WINDOWS),
        "pillars": pillars,
    }


def _ticker(value: Any) -> str:
    if not isinstance(value, str):
        raise ReportError("Enter a ticker.")
    ticker = value.strip().upper()
    if not ticker:
        raise ReportError("Enter a ticker.")
    if len(ticker) > 20:
        raise ReportError("Enter a ticker of up to 20 characters.")
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.&-")
    if any(character not in allowed for character in ticker):
        raise ReportError("Ticker may use letters, numbers, and . & - only.")
    if not ticker[0].isalnum():
        raise ReportError("Ticker must start with a letter or number.")
    return ticker


def _choice(value: Any, options: dict[str, Any], label: str) -> str:
    if not isinstance(value, str) or value not in options:
        names = ", ".join(options)
        raise ReportError(f"Choose {label}. Options: {names}.")
    return value


def _last_price(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, str):
        raise ReportError("Last price must be a plain number, or left blank.")
    text = value.strip().replace(",", "")
    for prefix in ("$", "₹"):
        if text.startswith(prefix):
            text = text[len(prefix) :].strip()
    if text == "":
        return None
    if not text.replace(".", "", 1).isdigit() or text.count(".") > 1:
        raise ReportError("Last price must be a positive number, or left blank.")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ReportError("Last price must be a positive number, or left blank.") from exc
    if amount <= 0 or amount >= Decimal("1000000000"):
        raise ReportError("Last price must be greater than 0 and under 1,000,000,000.")
    return format(amount, "f")


def _figure(
    label: str,
    *,
    status: str,
    status_label: str,
    note: str,
    value: str = "unavailable",
    source: str | None = None,
    as_of: str | None = None,
    freshness: str = NOT_CONNECTED_FRESHNESS,
    unit: str | None = None,
    stale: bool = True,
) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "source": source,
        "as_of": as_of,
        "status": status,
        "status_label": status_label,
        "freshness": freshness,
        "stale": stale,
        "note": note,
        "unit": unit,
    }


def _gap(label: str, note: str) -> dict[str, Any]:
    return _figure(
        label,
        status="data_not_connected",
        status_label="Data not connected",
        note=note,
        stale=True,
    )


def _missing_series(label: str, note: str) -> dict[str, Any]:
    return _figure(
        label,
        status="series_missing",
        status_label="Series missing",
        note=note,
        freshness="No sessions were supplied, so there is no as-of date.",
        stale=False,
    )


def _not_used(label: str, note: str) -> dict[str, Any]:
    return _figure(
        label,
        status="not_applicable",
        status_label="Not used on this venue",
        note=note,
        freshness="Not applicable. This record does not exist for the venue.",
        stale=False,
    )


def _fundamentals() -> dict[str, Any]:
    gap = (
        "No filings or fundamentals feed is connected. The figure is not estimated."
    )
    return {
        "number": 1,
        "title": "Fundamental Health Check",
        "kicker": "Filter first",
        "figures": [
            _gap("Revenue growth", gap),
            _gap("Profitability or cash burn", gap),
            _gap("Debt-to-equity", gap),
            _gap("Valuation versus sector peers", gap),
            _figure(
                "Catalysts",
                value="unknown",
                status="unknown",
                status_label="Unknown",
                note=(
                    "No filing, exchange calendar, or company release was returned. "
                    "Earnings dates are not invented."
                ),
                freshness="No event date was supplied, so nothing can be checked for freshness.",
                stale=False,
            ),
        ],
        "interpretation": (
            "No interpretation. Revenue, profitability, leverage, valuation, and "
            "catalyst dates were not returned by a source."
        ),
    }


def _trend(last_price: str | None, currency: str) -> dict[str, Any]:
    figures: list[dict[str, Any]] = []
    if last_price is None:
        figures.append(
            _gap(
                "Last price",
                "No price was typed in, and no quote feed is connected. "
                "A last price is not looked up.",
            )
        )
    else:
        figures.append(
            _figure(
                "Last price",
                value=last_price,
                source="User input",
                as_of=None,
                status="user_supplied",
                status_label="User supplied",
                unit=currency,
                note=(
                    "Shown because it was typed in. It is not a quote from a "
                    "market-data feed and it is not a trend."
                ),
                freshness=(
                    "No exchange timestamp. Fails the last-trade window "
                    "(latest completed regular session)."
                ),
                stale=True,
            )
        )
    figures.extend(
        [
            _missing_series("Daily trend", "Not stated. No OHLC was supplied."),
            _missing_series("Weekly trend", "Not stated. No OHLC was supplied."),
            _missing_series("Support", "Not computed. No OHLC was supplied."),
            _missing_series("Resistance", "Not computed. No OHLC was supplied."),
            _gap(
                "Volume versus the 20-day average",
                "No volume feed is connected, so the average is not computed.",
            ),
            _gap(
                "Volume versus the 50-day average",
                "No volume feed is connected, so the average is not computed.",
            ),
        ]
    )
    return {
        "number": 2,
        "title": "Price Trend and Volume Confirmation",
        "kicker": "Only from supplied bars",
        "figures": figures,
        "interpretation": (
            "Price and volume series missing. Trend, support, resistance, and "
            "up or down volume are not stated. A user-typed last price does not "
            "replace OHLC."
        ),
    }


def _pressure(group: str) -> dict[str, Any]:
    volume = _missing_series(
        "Up-day versus down-day volume (20–50 sessions)",
        "OHLC and volume were not supplied, so up-day versus down-day volume "
        "is not assessed.",
    )
    if group == "us":
        figures = [
            _gap(
                "13F buyer-to-seller ratio and dollar flows",
                "No 13F feed is connected. When one is, state the lag: positions "
                "are quarter-end and the filing can arrive up to 45 days later. "
                "The ratio is not estimated.",
            ),
            volume,
            _gap(
                "Form 4 open-market buys versus sells",
                "No Form 4 feed is connected. Count only open-market buys and "
                "sells. Exclude tax withholding and 10b5-1 plans. If a future "
                "source cannot separate those, the count stays unavailable.",
            ),
            _gap(
                "Short interest as a percent of float",
                "No short-interest feed is connected. Direction versus the prior "
                "report is not estimated.",
            ),
            _gap(
                "Days to cover",
                "Days-to-cover needs both short interest and average volume from "
                "a source. Neither was returned.",
            ),
            _not_used(
                "Shareholding pattern and FII/DII",
                "Those are the India flow record. They are not used for this "
                "US listing, and no FII or DII figure is estimated.",
            ),
        ]
        interpretation = (
            "US flow records (13F, Form 4, short interest) were not returned. "
            "No buyer-to-seller ratio is stated."
        )
    else:
        figures = [
            _not_used(
                "13F institutional filings",
                "13F is a US SEC filing. It is not used for NSE or BSE names. "
                "No 13F ratio or dollar flow is estimated.",
            ),
            _gap(
                "Shareholding pattern and stock-level FII/DII",
                "No shareholding feed is connected. The pattern is quarterly; "
                "state that lag when a source exists. Market-wide daily FII/DII "
                "cash totals are not a substitute for this stock.",
            ),
            _gap(
                "Bulk and block deals",
                "No exchange bulk or block file is connected. Deals are not estimated.",
            ),
            _gap(
                "Exchange short or SLB",
                "Report this only where the venue publishes it. Nothing was "
                "returned, so the value is unavailable, not zero.",
            ),
            volume,
            _gap(
                "Promoter and insider disclosures",
                "No exchange or SEBI insider, SAST, or pledge file is connected. "
                "These are not Form 4 filings and they are not 10b5-1 plans.",
            ),
        ]
        interpretation = (
            "India flow records (shareholding pattern, FII/DII, bulk and block "
            "deals, exchange short or SLB) were not returned. 13F language is "
            "not used for this listing."
        )
    return {
        "number": 3,
        "title": "Buying versus Selling Pressure",
        "kicker": "US 13F branch" if group == "us" else "India shareholding branch",
        "figures": figures,
        "interpretation": interpretation,
    }


def _alignment(group: str) -> dict[str, Any]:
    flow_name = (
        "13F, Form 4, or short interest"
        if group == "us"
        else "shareholding, FII/DII, bulk or block deals, or exchange short/SLB"
    )
    return {
        "number": 4,
        "title": "Signal Alignment and Divergence",
        "kicker": "Only when both sides exist",
        "figures": [
            _figure(
                "Flow versus the price trend",
                status="series_missing",
                status_label="Not assessed",
                note=(
                    f"Alignment cannot be assessed. The price series is missing, "
                    f"and no {flow_name} series was returned."
                ),
                freshness="Nothing to date. Confirmation and divergence are not stated.",
                stale=False,
            ),
            _figure(
                "Accumulation versus short covering",
                status="data_not_connected",
                status_label="Data not connected",
                note=(
                    "Short interest or SLB was not supplied, so a price move cannot "
                    "be labeled short covering or long-term accumulation."
                ),
            ),
        ],
        "interpretation": (
            "No divergence is claimed. Buying versus selling pressure cannot "
            "confirm or contradict a trend that was not supplied."
        ),
    }


def _summary(group: str, last_price: str | None, currency: str) -> dict[str, Any]:
    if group == "us":
        flow_gap = (
            "13F, Form 4 open-market trades, short interest, and days-to-cover "
            "were not returned."
        )
        flow_watch = (
            "A 13F filing with its quarter-end and filing date, Form 4 rows that "
            "already exclude tax withholding and 10b5-1 plans, and a short-interest "
            "publication with average volume if days-to-cover is needed."
        )
    else:
        flow_gap = (
            "The shareholding pattern, stock-level FII/DII, bulk and block deals, "
            "and exchange short or SLB were not returned. 13F is not the record "
            "for this venue."
        )
        flow_watch = (
            "The latest quarterly shareholding pattern, exchange bulk and block "
            "deals, and an exchange short or SLB file only if that venue publishes one."
        )

    watch = [
        {
            "text": "Price levels are unknown until OHLC is supplied by a source.",
            "cites": "Fact missing. Support and resistance were not computed.",
        },
        {
            "text": (
                "Volume versus the 20-day and 50-day averages is unknown until "
                "volume is supplied."
            ),
            "cites": "Fact missing. No volume series was returned.",
        },
        {
            "text": f"Flow to watch next: {flow_watch}",
            "cites": "Fact missing. No flow source was called.",
        },
        {
            "text": (
                "The next catalyst is unknown. No earnings date or other event "
                "was supplied by a source."
            ),
            "cites": "Fact missing. Catalyst dates are unknown.",
        },
    ]
    if last_price is not None:
        watch.append(
            {
                "text": (
                    f"A last price of {last_price} {currency} was typed in. It has "
                    f"no exchange timestamp, so it is not a level to treat as the market."
                ),
                "cites": "Sourced fact: user input on this form. Not a market-data feed.",
            }
        )

    return {
        "number": 5,
        "title": "Objective Summary and Risk Checklist",
        "kicker": "Cite a fact, or say it is missing",
        "groups": [
            {
                "title": "Bullish factors",
                "bullets": [
                    {
                        "text": (
                            "No sourced fact shows revenue growth, profitability, "
                            "or a valuation versus peers."
                        ),
                        "cites": "Fact missing. Fundamentals were not returned.",
                    },
                    {
                        "text": (
                            "No sourced fact shows buying pressure confirming an "
                            "uptrend."
                        ),
                        "cites": (
                            "Fact missing. The price series and the flow series "
                            "were not returned."
                        ),
                    },
                ],
            },
            {
                "title": "Bearish risks and traps",
                "bullets": [
                    {
                        "text": (
                            "The price and volume series is missing, so support, "
                            "resistance, and accumulation cannot be checked."
                        ),
                        "cites": "Fact missing. OHLC and volume were not supplied.",
                    },
                    {
                        "text": flow_gap,
                        "cites": "Fact missing. The venue flow feed is not connected.",
                    },
                    {
                        "text": (
                            "Catalyst dates are unknown. No earnings date was "
                            "supplied, and none is assumed."
                        ),
                        "cites": "Fact missing. No dated event was returned.",
                    },
                ],
            },
            {
                "title": "What to watch next",
                "bullets": watch,
            },
        ],
        "interpretation": (
            "The checklist records gaps. It is not a recommendation to buy or "
            "sell, and it does not promise an outcome."
        ),
    }
