import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from odds_client import fetch_odds, fetch_all_odds, SPORTS
from arbitrage import find_arbitrage
from kalshi_client import fetch_kalshi_sport_data, fetch_all_kalshi_sports, SPORT_SERIES

load_dotenv()

app = Flask(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
API_KEY = os.getenv("ODDS_API_KEY", "")


def _require_key():
    if not API_KEY:
        return None
    return API_KEY


@app.route("/api/sports")
def list_sports():
    return jsonify([
        {"key": "americanfootball_nfl", "title": "NFL"},
        {"key": "basketball_nba", "title": "NBA"},
        {"key": "baseball_mlb", "title": "MLB"},
        {"key": "icehockey_nhl", "title": "NHL"},
    ])


@app.route("/api/odds")
def get_odds():
    key = _require_key()
    if not key:
        return jsonify({"error": "ODDS_API_KEY not configured"}), 500
    sport = request.args.get("sport")
    try:
        if sport and sport in SPORTS:
            games = fetch_odds(key, sport)
        else:
            games = fetch_all_odds(key)
        print(f"[DEBUG] Fetched {len(games)} games for sport={sport}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch odds: {e}")
        games = []
    return jsonify(games)


@app.route("/api/arbitrage")
def get_arbitrage():
    key = _require_key()
    if not key:
        return jsonify({"error": "ODDS_API_KEY not configured"}), 500
    sport = request.args.get("sport")
    try:
        if sport and sport in SPORTS:
            games = fetch_odds(key, sport)
        else:
            games = fetch_all_odds(key)
    except Exception:
        games = []
    return jsonify(find_arbitrage(games))


@app.route("/api/kalshi")
def get_kalshi():
    sport = request.args.get("sport")
    try:
        if sport and sport in SPORT_SERIES:
            data = fetch_kalshi_sport_data(sport)
            for item in data:
                item["sport_key"] = sport
        else:
            data = fetch_all_kalshi_sports()
        print(f"[DEBUG] Fetched {len(data)} Kalshi events for sport={sport}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch Kalshi data: {e}")
        data = []
    return jsonify(data)


@app.route("/")
def serve_index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(FRONTEND_DIR), filename)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
