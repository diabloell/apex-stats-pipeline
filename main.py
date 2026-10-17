import json

with open("data/scores.json", encoding="utf-8") as file:
    data = json.load(file)
placement_points = {
    1: 12,
    2: 9,
    3: 7,
    4: 5,
    5: 4,
    6: 3,
    7: 3,
    8: 2,
    9: 2,
    10: 2,
    11: 1,
    12: 1,
    13: 1,
    14: 1,
    15: 1,
    16: 0,
    17: 0,
    18: 0,
    19: 0,
    20: 0
}


def team_kills(match):
    team_kills = {}
    for player in match["data"]:
        team_name = player["team_name"]
        team_kills[team_name] = team_kills.get(team_name, 0) + player["kills"]

    return team_kills


def team_placements(match):
    team_placements = {}
    for team in match["data"]:
        team_placement = team["team_placement"]
        team_name = team["team_name"]
        team_placements[team_name] = team_placement
    return team_placements


def calculate_points(match):
    team_points = {}
    kills = team_kills(match)
    placements = team_placements(match)

    for team_name, placement in placements.items():
        team_points[team_name] = placement_points[placement] + kills[team_name]

    return team_points


def calculate_day(data):
    day_points = {}

    for match in data["matches"]:
        cur_match = calculate_points(match)
        for team_name, points in cur_match.items():
            day_points[team_name] = day_points.get(team_name, 0) + points

    return day_points


def match_scores(data):
    day_points = {}

    for match in data["matches"]:
        cur_match = calculate_points(match)
        for team_name, points in cur_match.items():
            day_points.setdefault(team_name, []).append(points)
    return day_points


def tiebreaker_scores(data):
    sorted_scores = {}
    for team, scores in data.items():
        sorted_scores[team] = sorted(scores, reverse=True)
    return sorted_scores

def get_standings(day_points, tie_scores, tie_placements, tie_kills):
    standings = sorted(
        day_points.items(),
        key=lambda x: (
            x[1],
            tie_scores[x[0]],
            [-p for p in tie_placements[x[0]]],
            tie_kills[x[0]]
        ),
        reverse=True
    )
    return standings


def match_placements(data):
    placements = {}
    for match in data["matches"]:
        cur_match = team_placements(match)

        for team_name, placement in cur_match.items():
            placements.setdefault(team_name, []).append(placement)
    return placements


def tiebreaker_placements(data):
    sorted_placements = {}
    for team, placement in data.items():
        sorted_placements[team] = sorted(placement)
    return sorted_placements

def match_kills(data):
    kills = {}
    for match in data["matches"]:
        cur_match = team_kills(match)

        for team_name, kill in cur_match.items():
            kills.setdefault(team_name, []).append(kill)
    return kills


def match_point_eligible(data, threshold=50):
    total_points = {}
    eligible_after = {}
    for match_number, match in enumerate(data["matches"], start=1):
        current_points = calculate_points(match)

        for team_name, points in current_points.items():
            total_points[team_name] = total_points.get(team_name, 0) + points

            if total_points[team_name] >= threshold and team_name not in eligible_after:
                eligible_after[team_name] = match_number
    return eligible_after




def match_point_winner(data, threshold=50):
    eligible_after = match_point_eligible(data, threshold)

    for match_number, match in enumerate(data["matches"], start=1):
        placements = team_placements(match)

        for team_name, placement in placements.items():
            if placement == 1:
                if team_name in eligible_after and eligible_after[team_name] < match_number:
                    return team_name

    return None

day_points = calculate_day(data)
tie_scores = tiebreaker_scores(match_scores(data))
tie_placements = tiebreaker_placements(match_placements(data))
tie_kills = tiebreaker_scores(match_kills(data))

standings = get_standings(day_points, tie_scores, tie_placements, tie_kills)

print(standings)
print(match_point_eligible(data))
print(match_point_winner(data))
