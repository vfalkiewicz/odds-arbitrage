def american_to_decimal(american):
    if american > 0:
        return (american / 100) + 1
    return (100 / abs(american)) + 1


def _check_arb(best_odds):
    """Check if a set of best odds constitutes an arbitrage opportunity."""
    if len(best_odds) < 2:
        return None

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
        return profit_pct, arb_outcomes
    return None


def find_arbitrage(games):
    opportunities = []

    for game in games:
        bookmakers = game.get("bookmakers", [])
        market_keys = set()
        for bk in bookmakers:
            for m in bk.get("markets", []):
                market_keys.add(m["key"])

        for market_key in market_keys:
            if market_key == "h2h":
                # Moneyline: no points, just compare outcome names directly
                best_odds = {}
                for bk in bookmakers:
                    for m in bk.get("markets", []):
                        if m["key"] != market_key:
                            continue
                        for outcome in m.get("outcomes", []):
                            decimal = american_to_decimal(outcome["price"])
                            label = outcome["name"]
                            american = outcome["price"]
                            if label not in best_odds or decimal > best_odds[label][0]:
                                best_odds[label] = (decimal, bk["title"], None, american)

                result = _check_arb(best_odds)
                if result:
                    profit_pct, arb_outcomes = result
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

            elif market_key in ("spreads", "totals"):
                # Group by point value -- only compare same lines across books
                point_groups = {}
                for bk in bookmakers:
                    for m in bk.get("markets", []):
                        if m["key"] != market_key:
                            continue
                        for outcome in m.get("outcomes", []):
                            point = outcome.get("point")
                            if point is None:
                                continue
                            # For spreads: group by abs(point) since one team is +X and the other is -X
                            # For totals: group by point value since Over and Under share the same number
                            group_key = abs(point)
                            if group_key not in point_groups:
                                point_groups[group_key] = {}

                            decimal = american_to_decimal(outcome["price"])
                            label = outcome["name"]
                            american = outcome["price"]

                            if label not in point_groups[group_key] or decimal > point_groups[group_key][label][0]:
                                point_groups[group_key][label] = (decimal, bk["title"], point, american)

                for point_val, best_odds in point_groups.items():
                    result = _check_arb(best_odds)
                    if result:
                        profit_pct, arb_outcomes = result
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
