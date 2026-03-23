#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
import json
from pathlib import Path
import argparse


DEFAULT_MANIFEST = Path("project/manifest.json")
DEFAULT_OUTPUT = Path("USERS.md")  

def load_manifest(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_entries(manifest):
    entries = manifest.get("entries", [])
    return [
        e for e in entries
        if e.get("type") in ("user", "teg")
    ]


def sort_entries(entries):
    # row, col で並べる（左上→右→下）
    return sorted(entries, key=lambda e: (e.get("row", 0), e.get("col", 0)))


def format_run_id(e):
    run_id = e.get("sourceRunId")
    return run_id if run_id else "-"


def generate_markdown(entries):
    lines = []

    lines.append("# OpenSUSI MPW Users\n")
    lines.append("| Tile | X (um) | Y (um) | GitHub ID | Top Cell | Run ID |")
    lines.append("|------|--------|--------|-----------|----------|--------|")

    for e in entries:
        row = e.get("row")
        col = e.get("col")
        x = int(round(e.get("x", 0)))
        y = int(round(e.get("y", 0)))
        github = e.get("githubId", "-")
        top = e.get("gdsTopCell", "-")
        run_id = format_run_id(e)

        tile = f"({col},{row})"

        lines.append(
            f"| {tile} | {x} | {y} | {github} | {top} | {run_id} |"
        )

    lines.append("")  # newline
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate USERS.md from manifest.json")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    print(f"manifest : {manifest_path}")
    print(f"output   : {output_path}")

    manifest = load_manifest(manifest_path)
    entries = filter_entries(manifest)
    entries = sort_entries(entries)

    md = generate_markdown(entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")

    print(f"DONE: wrote {output_path}")
    print(f"entries: {len(entries)}")


if __name__ == "__main__":
    main()