import json
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from stats import placement_points

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ApexStatsPipeline/1.0)"}

def _number(value):
    return int(re.sub(r"[^\d-]", "", str(value)))

def parse_score_matrix(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.score-matrix_table")
    if table is None:
        raise ValueError("No score matrix found. Select an ALS STAGE URL with results, not Overview.")
    head_games = table.select("thead th.score-matrix_cell-game")
    game_count = len(head_games)
    if game_count < 1:
        raise ValueError("No individual games were found in the ALS score matrix.")

    matches = [
        {"id": f"als_game_{i+1}", "map": None, "start_time": None,
         "players": [], "teams": []}
        for i in range(game_count)
    ]
    totals = {}
    for row in table.select("tbody tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3 + 2 * game_count:
            raise ValueError(f"Score matrix row has {len(cells)} cells; expected at least {3+2*game_count}.")
        team_cell = cells[1]
        span = team_cell.find("span")
        name = span.get_text(" ", strip=True) if span else team_cell.get_text(" ", strip=True)
        if not name:
            raise ValueError("Found a row without a team name.")
        totals[name] = _number(cells[2].get_text(" ", strip=True))
        for i in range(game_count):
            p = cells[3 + 2*i].get_text(" ", strip=True)
            k = cells[4 + 2*i].get_text(" ", strip=True)
            if not p or p in {"-", "N/A"}:
                continue
            place, kills = _number(p), _number(k or "0")
            if not 1 <= place <= 20 or kills < 0:
                raise ValueError(f"Unreasonable result for {name}, game {i+1}: {place=}, {kills=}")
            matches[i]["teams"].append({"name": name, "placement": place, "kills": kills})

    if not totals:
        raise ValueError("The score matrix contains no teams.")

    warnings = []

    site_standings = [
        {"position": i, "team": name, "points": points}
        for i, (name, points) in enumerate(totals.items(), start=1)
    ]
    for team, website_total in totals.items():
        recalculated = sum(
            placement_points[row["placement"]] + row["kills"]
            for match in matches for row in match["teams"] if row["name"] == team
        )
        if recalculated != website_total:
            warnings.append(
                f"{team}: site total {website_total}, calculated {recalculated} "
                "(possible starting points, penalty or missing game)"
            )

    return {"source": "als", "matches": matches, "site_standings": site_standings,
            "warnings": warnings}

def parse_game_links(html, stage_url):
    soup = BeautifulSoup(html, "html.parser")
    links = {}
    for banner in soup.select(".replay-banner_container"):
        heading = banner.select_one(".replay-banner_title")
        if not heading:
            continue
        heading_text = heading.get_text(" ", strip=True)
        found = re.search(r"Game\s*#(\d+)\s*-\s*(.+)", heading_text, re.I)
        if not found:
            continue
        number, map_name = int(found.group(1)), found.group(2).strip()
        game_link = None
        for link in banner.find_all("a", href=True):
            if "View game stats" in link.get_text(" ", strip=True):
                game_link = urljoin(stage_url, link["href"])
                break
        if game_link:
            links[number] = {"url": game_link, "map": map_name, "banner": banner}
    return links

def _legend_by_player(banner):
    result = {}
    if banner is None:
        return result
    for button in banner.select("button[onclick]"):
        script = button.get("onclick", "")
        if "showLobbyLayout(" not in script:
            continue
        match = re.search(r"showLobbyLayout\s*\(\s*(\{.*\})\s*\)", script, flags=re.S)
        if not match:
            continue
        try:
            groups = json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            continue
        for team in groups.values():
            for player in (team.get("players") or {}).values():
                name, legend = player.get("name", ""), player.get("legend", "")
                if name and legend:
                    result[name.casefold().strip()] = legend
    return result

def _slug_legend(text):
    return re.sub(r"[^a-z0-9]", "", text.casefold())

def parse_game_players(html, legends=None):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one('table[data-column-manager="players-stats"]')
    if table is None:
        raise ValueError("Players Statistics table is missing from this game page.")
    rows = table.find_all("tr")
    if not rows:
        raise ValueError("Player statistics table is empty.")
    headings = [th.get_text(" ", strip=True).casefold() for th in rows[0].find_all("th")]
    expected = ("player", "team", "kills", "dmg dealt")
    missing = [h for h in expected if h not in headings]
    if missing:
        raise ValueError(f"Missing columns on ALS player stats page: {missing}")
    indices = {h: headings.index(h) for h in expected}
    result = []
    legends = legends or {}
    for row in rows[1:]:
        cells = row.find_all("td", recursive=False)
        if len(cells) < len(headings):
            continue
        name_cell = cells[indices["player"]]
        link = name_cell.select_one("a.algs-player-page-link")
        name = link.get_text(" ", strip=True) if link else name_cell.get_text(" ", strip=True)
        team = cells[indices["team"]].get_text(" ", strip=True)
        if not name or not team:
            continue
        kills = _number(cells[indices["kills"]].get_text(" ", strip=True))
        damage = _number(cells[indices["dmg dealt"]].get_text(" ", strip=True))
        result.append({"name": name, "team": team, "kills": kills,
                       "damage": damage, "legend": _slug_legend(legends.get(name.casefold().strip(), "")),
                       "placement": None})
    if not result:
        raise ValueError("No player statistics were extracted from ALS game page.")
    return result

def get_als_results(stage_url, fetch_players=True, timeout=25):
    parsed = urlparse(stage_url)
    if parsed.scheme not in {"https", "http"} or parsed.hostname not in {
        "apexlegendsstatus.com", "www.apexlegendsstatus.com", "mirg.apexlegendsstatus.com"
    }:
        raise ValueError("Use an apexlegendsstatus.com stage URL.")

    session = requests.Session()
    session.headers.update(HEADERS)

    def get(url):
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text

    stage_html = get(stage_url)
    day = parse_score_matrix(stage_html)
    links = parse_game_links(stage_html, stage_url)
    for index, match in enumerate(day["matches"], start=1):
        info = links.get(index)
        if not info:
            day["warnings"].append(f"Game {index}: detail page link not found")
            continue
        match["id"] = info["url"].rsplit("/", 1)[-1]
        match["map"] = info["map"]
        date = info["banner"].select_one(".replay-banner_date[data-timestamp]")
        match["start_time"] = date.get("data-timestamp") if date else None
        if not fetch_players:
            continue
        try:
            players = parse_game_players(get(info["url"]), _legend_by_player(info["banner"]))
            placement_by_team = {x["name"].casefold(): x["placement"] for x in match["teams"]}
            for player in players:
                player["placement"] = placement_by_team.get(player["team"].casefold())
            match["players"] = players
            unmatched = sum(1 for p in players if p["placement"] is None)
            if unmatched:
                day["warnings"].append(f"Game {index}: {unmatched} players with unmatched team names")
            missing_legends = sum(1 for p in players if not p["legend"])
            if missing_legends:
                day["warnings"].append(f"Game {index}: legends missing for {missing_legends} players")
        except (requests.RequestException, ValueError) as exc:
            day["warnings"].append(f"Game {index}: individual statistics unavailable: {exc}")
    return day
