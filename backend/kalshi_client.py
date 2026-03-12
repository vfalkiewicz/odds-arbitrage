import json
import ssl
import urllib.request
import urllib.parse
import re

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

SPORT_SERIES = {
    "basketball_nba": {
        "game": "KXNBAGAME",
        "spread": "KXNBASPREAD",
        "total": "KXNBATEAMTOTAL",
    },
    "baseball_mlb": {
        "game": "KXMLBGAME",
        "spread": "KXMLBSPREAD",
        "total": "KXMLBTEAMTOTAL",
    },
    "icehockey_nhl": {
        "game": "KXNHLGAME",
        "spread": "KXNHLSPREAD",
        "total": "KXNHLTEAMTOTAL",
    },
    "americanfootball_nfl": {
        "game": "KXNFLGAME",
        "spread": "KXNFLSPREAD",
        "total": "KXNFLTEAMTOTAL",
    },
}

TEAM_ABBREVS = {
    "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte",
    "CHI": "Chicago", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver",
    "DET": "Detroit", "GSW": "Golden State", "HOU": "Houston", "IND": "Indiana",
    "LAC": "Los Angeles C", "LAL": "Los Angeles L", "MEM": "Memphis",
    "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota", "NOP": "New Orleans",
    "NYK": "New York", "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia",
    "PHX": "Phoenix", "POR": "Portland", "SAC": "Sacramento", "SAS": "San Antonio",
    "TOR": "Toronto", "UTA": "Utah", "WAS": "Washington",
    # NHL
    "ANA": "Anaheim", "ARI": "Arizona", "BUF": "Buffalo", "CGY": "Calgary",
    "CAR": "Carolina", "COL": "Colorado", "CBJ": "Columbus", "EDM": "Edmonton",
    "FLA": "Florida", "LA": "Los Angeles", "NJ": "New Jersey", "NSH": "Nashville",
    "NYI": "NY Islanders", "NYR": "NY Rangers", "OTT": "Ottawa", "PIT": "Pittsburgh",
    "SEA": "Seattle", "SJ": "San Jose", "STL": "St. Louis", "TB": "Tampa Bay",
    "VAN": "Vancouver", "VGK": "Vegas", "WPG": "Winnipeg",
    # MLB
    "BAL": "Baltimore", "CIN": "Cincinnati", "KC": "Kansas City", "SD": "San Diego",
    "SF": "San Francisco", "TEX": "Texas", "WSH": "Washington",
    "LAA": "LA Angels", "LAD": "LA Dodgers", "CWS": "Chicago Sox",
    "TB": "Tampa Bay", "MIL": "Milwaukee",
}


def _get(path, params=None):
    qs = ""
    if params:
        qs = "?" + urllib.parse.urlencode(params)
    url = f"{BASE_URL}{path}{qs}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _kalshi_price_to_american(yes_price):
    if yes_price is None or yes_price <= 0 or yes_price >= 1:
        return None
    if yes_price >= 0.5:
        return round(-100 * yes_price / (1 - yes_price))
    else:
        return round(100 * (1 - yes_price) / yes_price)


def _kalshi_price_to_decimal(yes_price):
    if yes_price is None or yes_price <= 0:
        return None
    return round(1 / yes_price, 3)


def _parse_point_from_title(title):
    match = re.search(r'over\s+([\d.]+)', title, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _extract_game_label(event_ticker, series_prefix):
    """Extract a human-readable game label from the event ticker."""
    suffix = event_ticker.replace(series_prefix + "-", "")
    # Remove the date prefix like "26MAR12"
    cleaned = re.sub(r'^\d+[A-Z]{3}\d+', '', suffix)
    # Try to split into two team abbreviations
    teams = []
    remaining = cleaned
    for abbr in sorted(TEAM_ABBREVS.keys(), key=len, reverse=True):
        if remaining.startswith(abbr):
            teams.append(TEAM_ABBREVS[abbr])
            remaining = remaining[len(abbr):]
        elif remaining == abbr:
            teams.append(TEAM_ABBREVS[abbr])
            remaining = ""
    if len(teams) >= 2:
        return f"{teams[0]} vs {teams[1]}"
    return cleaned


def fetch_kalshi_markets(series_ticker, status="open"):
    all_markets = []
    cursor = None
    while True:
        params = {"limit": 1000, "status": status, "series_ticker": series_ticker}
        if cursor:
            params["cursor"] = cursor
        data = _get("/markets", params)
        markets = data.get("markets", [])
        all_markets.extend(markets)
        cursor = data.get("cursor", "")
        if not cursor or len(markets) == 0:
            break
    return all_markets


def _group_by_event(markets):
    events = {}
    for m in markets:
        et = m.get("event_ticker", "")
        if et not in events:
            events[et] = []
        events[et].append(m)
    return events


def fetch_kalshi_sport_data(sport_key):
    series_map = SPORT_SERIES.get(sport_key)
    if not series_map:
        return []

    results = []

    # Game winner (moneyline)
    try:
        markets = fetch_kalshi_markets(series_map["game"])
        for event_ticker, event_markets in _group_by_event(markets).items():
            game_label = event_markets[0].get("title", "") or _extract_game_label(event_ticker, series_map["game"])
            outcomes = []
            for m in event_markets:
                yes_bid = float(m.get("yes_bid_dollars", 0) or 0)
                yes_ask = float(m.get("yes_ask_dollars", 0) or 0)
                mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_bid or yes_ask
                ticker_parts = m["ticker"].split("-")
                team_abbrev = ticker_parts[-1] if len(ticker_parts) > 1 else ""
                team_name = TEAM_ABBREVS.get(team_abbrev, team_abbrev)
                if mid > 0:
                    outcomes.append({
                        "outcome_name": team_name,
                        "ticker": m["ticker"],
                        "yes_bid": yes_bid,
                        "yes_ask": yes_ask,
                        "mid_price": round(mid, 4),
                        "american_odds": _kalshi_price_to_american(mid),
                        "decimal_odds": _kalshi_price_to_decimal(mid),
                        "point": None,
                    })
            if outcomes:
                results.append({
                    "event_ticker": event_ticker,
                    "title": game_label,
                    "market_type": "h2h",
                    "outcomes": outcomes,
                    "sport_key": sport_key,
                })
    except Exception as e:
        print(f"[KALSHI] Error fetching game markets: {e}")

    # Spreads
    try:
        markets = fetch_kalshi_markets(series_map["spread"])
        for event_ticker, event_markets in _group_by_event(markets).items():
            game_label = _extract_game_label(event_ticker, series_map["spread"])
            outcomes = []
            for m in event_markets:
                yes_bid = float(m.get("yes_bid_dollars", 0) or 0)
                yes_ask = float(m.get("yes_ask_dollars", 0) or 0)
                mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_bid or yes_ask
                point = _parse_point_from_title(m.get("title", ""))
                ticker_parts = m["ticker"].split("-")
                team_part = ticker_parts[-1] if len(ticker_parts) > 1 else ""
                team_abbrev = re.sub(r'\d+$', '', team_part)
                team_name = TEAM_ABBREVS.get(team_abbrev, team_abbrev)
                if mid > 0:
                    outcomes.append({
                        "outcome_name": f"{team_name} -{point}" if point else team_name,
                        "ticker": m["ticker"],
                        "yes_bid": yes_bid,
                        "yes_ask": yes_ask,
                        "mid_price": round(mid, 4),
                        "american_odds": _kalshi_price_to_american(mid),
                        "decimal_odds": _kalshi_price_to_decimal(mid),
                        "point": point,
                    })
            if outcomes:
                outcomes.sort(key=lambda o: o["point"] or 0)
                results.append({
                    "event_ticker": event_ticker,
                    "title": f"{game_label} (Spread)",
                    "market_type": "spreads",
                    "outcomes": outcomes,
                    "sport_key": sport_key,
                })
    except Exception as e:
        print(f"[KALSHI] Error fetching spread markets: {e}")

    # Totals
    try:
        markets = fetch_kalshi_markets(series_map["total"])
        for event_ticker, event_markets in _group_by_event(markets).items():
            game_label = _extract_game_label(event_ticker, series_map["total"])
            outcomes = []
            for m in event_markets:
                yes_bid = float(m.get("yes_bid_dollars", 0) or 0)
                yes_ask = float(m.get("yes_ask_dollars", 0) or 0)
                mid = (yes_bid + yes_ask) / 2 if yes_bid and yes_ask else yes_bid or yes_ask
                point = _parse_point_from_title(m.get("title", ""))
                if mid > 0:
                    outcomes.append({
                        "outcome_name": f"Over {point}" if point else m.get("title", ""),
                        "ticker": m["ticker"],
                        "yes_bid": yes_bid,
                        "yes_ask": yes_ask,
                        "mid_price": round(mid, 4),
                        "american_odds": _kalshi_price_to_american(mid),
                        "decimal_odds": _kalshi_price_to_decimal(mid),
                        "point": point,
                    })
            if outcomes:
                outcomes.sort(key=lambda o: o["point"] or 0)
                results.append({
                    "event_ticker": event_ticker,
                    "title": f"{game_label} (Totals)",
                    "market_type": "totals",
                    "outcomes": outcomes,
                    "sport_key": sport_key,
                })
    except Exception as e:
        print(f"[KALSHI] Error fetching totals markets: {e}")

    return results


def fetch_all_kalshi_sports():
    all_data = []
    for sport_key in SPORT_SERIES:
        try:
            data = fetch_kalshi_sport_data(sport_key)
            all_data.extend(data)
        except Exception as e:
            print(f"[KALSHI] Error fetching {sport_key}: {e}")
    return all_data
