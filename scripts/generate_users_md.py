#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("project/manifest.json")
DEFAULT_OUTPUT = Path("USERS.md")


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in manifest.get("entries", [])
        if entry.get("type") in {"user", "teg"}
    ]


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: (e.get("row", 0), e.get("col", 0)))


def format_run_id(entry: dict[str, Any]) -> str:
    return entry.get("sourceRunId") or "-"


def format_tile(entry: dict[str, Any]) -> str:
    row = entry.get("row")
    col = entry.get("col")

    if row is None or col is None:
        return "-"

    return f"({col},{row})"


def generate_markdown(entries: list[dict[str, Any]]) -> str:
    lines = [
        "# OpenSUSI MPW Users",
        "",
        "| Tile | X (um) | Y (um) | GitHub ID | Top Cell | Run ID |",
        "|------|--------|--------|-----------|----------|--------|",
    ]

    for entry in entries:
        x = int(round(entry.get("x", 0)))
        y = int(round(entry.get("y", 0)))
        github_id = entry.get("githubId", "-")
        top_cell = entry.get("gdsTopCell", "-")
        run_id = format_run_id(entry)
        tile = format_tile(entry)

        lines.append(
            f"| {tile} | {x} | {y} | {github_id} | {top_cell} | {run_id} |"
        )

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate USERS.md from manifest.json"
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    manifest_path = Path(args.manifest)
    output_path = Path(args.output)

    print(f"manifest : {manifest_path}")
    print(f"output   : {output_path}")

    manifest = load_manifest(manifest_path)
    entries = sort_entries(filter_entries(manifest))
    markdown = generate_markdown(entries)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"DONE: wrote {output_path}")
    print(f"entries: {len(entries)}")


if __name__ == "__main__":
    main()