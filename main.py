"""Run this file first. Photoshop will fill PSD layers from the generated JSON."""

import argparse
import json
from pathlib import Path

from export_photoshop import export_table, export_mvp
from player_names import find_unknown_game_names
from stats import normalize_day

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Export ALGS results for Photoshop PSD templates")
    parser.add_argument("--match", type=int, default=5, help="MVP match number (default: 5)")
    parser.add_argument("--event", default="ALGS CHAMPIONSHIP 2025", help="Header for the templates")
    args = parser.parse_args()

    source = ROOT / "data" / "scores.json"
    if not source.is_file():
        raise FileNotFoundError(f"Missing tournament data: {source}")
    with source.open(encoding="utf-8") as file:
        data = normalize_day(json.load(file))

    table_job = export_table(data, args.event)
    mvp_job, has_photo = export_mvp(data, args.match, args.event)

    print(f"Table JSON: {table_job}")
    print(f"Match MVP JSON: {mvp_job}")
    if not has_photo:
        print("NOTE: no prepared photo for this MVP. The Photoshop result is a draft, not ready to publish.")
    unknown = find_unknown_game_names(data)
    if unknown:
        print(f"Unknown player names: {len(unknown)} (add their aliases to player_names.py if needed)")
        for name, team in unknown[:10]:
            print(f"  {name} ({team})")
    print("Next: Photoshop > File > Scripts > Browse > photoshop/fill_from_json.jsx")
    print("Select table.json or mvp_match_*.json when prompted.")


if __name__ == "__main__":
    main()
