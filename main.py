import argparse
import json
from pathlib import Path

from export_photoshop import export_table, export_mvp
from player_names import find_unknown_game_names
from stats import normalize_day

ROOT = Path(__file__).resolve().parent

def prepare_data(source, als_url=None, fast=False):
    if source == "eternal":
        path = ROOT / "data" / "scores.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing Eternal Esports JSON: {path}")
        with path.open(encoding="utf-8") as file:
            return normalize_day(json.load(file))
    if not als_url:
        raise ValueError("Provide --als-url with a specific ALGS stage page")
    from als_parser import get_als_results
    return get_als_results(als_url, fetch_players=not fast)

def build_jobs(source="eternal", match_number=5, event="ALGS CHAMPIONSHIP 2025",
               job_type="both", als_url=None, fast=False):
    data = prepare_data(source, als_url=als_url, fast=fast)
    jobs = []
    if job_type in {"both", "table"}:
        jobs.append(export_table(data, event))
    if job_type in {"both", "mvp"}:
        job, _ = export_mvp(data, match_number, event)
        jobs.append(job)
    return jobs, data

def main():
    parser = argparse.ArgumentParser(description="Prepare editable Photoshop result posts")
    parser.add_argument("--source", choices=["eternal", "als"], default="eternal")
    parser.add_argument("--als-url", help="ALS stage URL for a specific tournament group/round")
    parser.add_argument("--match", type=int, default=5)
    parser.add_argument("--event", default="ALGS CHAMPIONSHIP 2025")
    parser.add_argument("--job", choices=["both", "table", "mvp"], default="both")
    parser.add_argument("--fast", action="store_true", help="ALS only: parse score matrix without per-game players")
    args = parser.parse_args()
    jobs, data = build_jobs(args.source, args.match, args.event, args.job, args.als_url, args.fast)
    for job in jobs:
        print("Photoshop JSON:", job)
    if args.source == "eternal":
        unknown = find_unknown_game_names(data)
        if unknown:
            print(f"Unknown nicknames: {len(unknown)}")
            for name, team in unknown[:10]:
                print(" -", name, f"({team})")
    for warning in data.get("warnings", []):
        print("WARNING:", warning)
    print("Photos are intentionally left for manual editing inside Photoshop.")

if __name__ == "__main__":
    main()
