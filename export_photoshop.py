import json
from pathlib import Path
from player_names import get_official_name
from stats import (
    calculate_day, get_standings, get_match_mvp_data,
    match_kills, match_placements, match_scores,
    tiebreaker_placements, tiebreaker_scores,
)

ROOT = Path(__file__).resolve().parent
EXPORT_DIR = ROOT / "output" / "photoshop"

def write_job(filename, payload):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    destination = EXPORT_DIR / filename
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination

def find_photo(official_name):
    folder = ROOT / "assets" / "players"
    if not folder.is_dir():
        return None
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".psd"}:
            if path.stem.casefold() == official_name.casefold():
                return path
    return None

def export_table(data, event_name):
    day_points = calculate_day(data)
    standings = get_standings(
        day_points,
        tiebreaker_scores(match_scores(data)),
        tiebreaker_placements(match_placements(data)),
        tiebreaker_scores(match_kills(data)),
    )
    kills = match_kills(data)
    if data.get("source") == "als" and data.get("site_standings"):

        rows = [
            {"position": row["position"], "team": row["team"],
             "kills": sum(kills.get(row["team"], [])), "points": row["points"]}
            for row in data["site_standings"][:20]
        ]
    else:
        rows = [
            {"position": position, "team": team, "kills": sum(kills[team]), "points": points}
            for position, (team, points) in enumerate(standings[:20], start=1)
        ]
    payload = {
        "type": "table",
        "event_name": event_name,
        "template_psd": "templates/table.psd",
        "output_psd": "output/photoshop/table_full.psd",
        "output_png": "output/photoshop/table_full.png",
        "rows": rows,
    }
    return write_job("table.json", payload)

def export_mvp(data, match_number, event_name):
    if not 1 <= match_number <= len(data["matches"]):
        raise ValueError(f"Match {match_number} not found: the file has {len(data['matches'])} matches")
    match = data["matches"][match_number - 1]
    prepared = get_match_mvp_data(match, match_number)
    players = []
    for player in prepared["top_players"]:
        players.append({
            "name": get_official_name(player["name"], player["team"]),
            "game_name": player["name"],
            "team": player["team"],
            "kills": player["kills"],
            "damage": player["damage"],
            "legend": player["legend"],
        })

    if not players:
        raise ValueError("The selected match has no players")

    mvp_photo = None
    payload = {
        "type": "match_mvp",
        "event_name": event_name,
        "match_number": match_number,
        "template_psd": "templates/match_mvp.psd",
        "output_psd": f"output/photoshop/mvp_match_{match_number}.psd",
        "output_png": f"output/photoshop/mvp_match_{match_number}.png",
        "players": players,
        "mvp_photo": mvp_photo.relative_to(ROOT).as_posix() if mvp_photo else None,
        "publication_ready": False,
    }
    return write_job(f"mvp_match_{match_number}.json", payload), bool(mvp_photo)
