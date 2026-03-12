import json
import ssl
import urllib.request
import urllib.parse

BASE_URL = "https://api.the-odds-api.com/v4"

SPORTS = [
    "americanfootball_nfl",
    "basketball_nba",
    "baseball_mlb",
    "icehockey_nhl",
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def fetch_odds(api_key, sport, markets="h2h,spreads,totals"):
    params = urllib.parse.urlencode({
        "apiKey": api_key,
        "regions": "us",
        "markets": markets,
        "oddsFormat": "american",
    })
    url = f"{BASE_URL}/sports/{sport}/odds?{params}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_all_odds(api_key):
    all_games = []
    for sport in SPORTS:
        try:
            games = fetch_odds(api_key, sport)
            all_games.extend(games)
        except Exception:
            continue
    return all_games
