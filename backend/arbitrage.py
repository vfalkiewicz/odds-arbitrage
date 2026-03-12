def american_to_decimal(american):
    if american > 0:
        return (american / 100) + 1
    return (100 / abs(american)) + 1


def find_arbitrage(games):
    opportunities = []

    for game in games:
        bookmakers = game.get("bookmakers", [])
        market_keys = set()
        for bk in bookmakers:
            for m in bk.get("markets", []):
                market_keys.add(m["key"])

        for market_key in market_keys:
            best_odds = {}

            for bk in bookmakers:
                for m in bk.get("markets", []):
                    if m["key"] != market_key:
                        continue
                    for outcome in m.get("outcomes", []):
                        decimal = american_to_decimal(outcome["price"])
                        label = outcome["name"]
                        point = outcome.get("point")
                        american = outcome["price"]
                        if label not in best_odds or decimal > best_odds[label][0]:
                            best_odds[label] = (decimal, bk["title"], point, american)

            if len(best_odds) < 2:
                continue

            inv_sum = sum(1 / odds for odds, _, _, _ in best_odds.values())

            if inv_sum < 1:
                profit_pct = round((1 / inv_sum - 1) * 100, 2)
                arb_outcomes = []
                for name, (odds, bookmaker, point, american) in best_odds.items():
                    stake_pct = round((1 / odds) / inv_sum * 100, 2)
                    arb_outcomes.append({
                        "outcome_name": name,
                        "bookmaker": bookmaker,
                        "odds": odds,
                        "stake_pct": stake_pct,
                        "point": point,
                        "american_odds": american,
                    })

                opportunities.append({
                    "game_id": game.get("id", ""),
                    "home_team": game.get("home_team", ""),
                    "away_team": game.get("away_team", ""),
                    "sport_key": game.get("sport_key", ""),
                    "sport_title": game.get("sport_title", ""),
                    "market": market_key,
                    "profit_pct": profit_pct,
                    "outcomes": arb_outcomes,
                })

    opportunities.sort(key=lambda o: o["profit_pct"], reverse=True)
    return opportunities
