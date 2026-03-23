#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
#!/usr/bin/env python3

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("project/manifest.json")
DEFAULT_OUTPUT = Path("USERS.svg")

DEFAULT_REPO_OWNER = "OpenSUSI"
DEFAULT_REPO_NAME = "OpenSUSI_MPW_TR2026"
DEFAULT_BRANCH = "main"

TILE_W = 140
TILE_H = 90
MARGIN = 30
HEADER_H = 40
ROW_LABEL_W = 30


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    entries = manifest.get("entries", [])
    return [e for e in entries if e.get("type") in ("teg", "user", "fill")]


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda e: (
            e.get("row", 9999) if e.get("row") is not None else 9999,
            e.get("col", 9999) if e.get("col") is not None else 9999,
        ),
    )


def repo_file_url(
    github_id: str,
    entry_type: str,
    repo_owner: str,
    repo_name: str,
    branch: str,
) -> str:
    if entry_type == "teg":
        rel = "users/00_system"
    elif entry_type == "fill":
        rel = "users/000_system"
    else:
        rel = f"users/{github_id}"

    return f"https://github.com/{repo_owner}/{repo_name}/blob/{branch}/{rel}"


def tile_screen_xy(col: int, row: int) -> tuple[int, int]:
    x = ROW_LABEL_W + MARGIN + col * TILE_W
    y = HEADER_H + MARGIN + row * TILE_H
    return x, y


def entry_label(entry: dict[str, Any]) -> tuple[str, str, str]:
    entry_type = entry.get("type", "")
    github_id = entry.get("githubId", "-")
    top = entry.get("gdsTopCell", "-")
    run_id = entry.get("sourceRunId") or "-"

    if entry_type == "teg":
        title = "TEG"
    elif entry_type == "fill":
        title = "FILL"
    else:
        title = github_id

    return title, top, str(run_id)


def css_class_for_entry(entry_type: str) -> str:
    if entry_type == "teg":
        return "tile tile-teg"
    if entry_type == "fill":
        return "tile tile-fill"
    return "tile tile-user"


def generate_svg(
    manifest: dict[str, Any],
    repo_owner: str,
    repo_name: str,
    branch: str,
) -> str:
    grid = manifest.get("grid", {})
    grid_x = int(grid.get("x", 8))
    grid_y = int(grid.get("y", 8))

    width = ROW_LABEL_W + MARGIN * 2 + grid_x * TILE_W
    height = HEADER_H + MARGIN * 2 + grid_y * TILE_H

    entries = sort_entries(filter_entries(manifest))

    by_tile: dict[tuple[int, int], dict[str, Any]] = {}
    for entry in entries:
        row = entry.get("row")
        col = entry.get("col")
        if row is None or col is None:
            continue
        by_tile[(col, row)] = entry

    parts: list[str] = []

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )

    parts.append(
        """<style>
text { font-family: Arial, sans-serif; fill: black; }
.tile { fill: white; stroke: black; stroke-width: 1; }
.tile-teg { fill: #f2f2f2; }
.tile-user { fill: #e8f2ff; }
.tile-fill { fill: #f7f7f7; }
.grid-label { font-size: 12px; }
.title { font-size: 18px; font-weight: bold; }
.tile-title { font-size: 13px; font-weight: bold; }
.tile-sub { font-size: 11px; }
.tile-run { font-size: 10px; }
</style>"""
    )

    parts.append(
        f'<text class="title" x="{MARGIN}" y="{MARGIN}">OpenSUSI MPW Users Layout</text>'
    )

    # Column labels
    for col in range(grid_x):
        x, _ = tile_screen_xy(col, 0)
        parts.append(
            f'<text class="grid-label" x="{x + TILE_W / 2}" y="{HEADER_H + 15}" '
            f'text-anchor="middle">{col}</text>'
        )

    # Row labels
    for row in range(grid_y):
        _, y = tile_screen_xy(0, row)
        parts.append(
            f'<text class="grid-label" x="{ROW_LABEL_W + MARGIN - 10}" y="{y + TILE_H / 2}" '
            f'text-anchor="end" dominant-baseline="middle">{row}</text>'
        )

    # Tiles
    for row in range(grid_y):
        for col in range(grid_x):
            x, y = tile_screen_xy(col, row)
            entry = by_tile.get((col, row))

            if entry is None:
                parts.append(
                    f'<rect class="tile" x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" />'
                )
                parts.append(
                    f'<text class="tile-sub" x="{x + TILE_W / 2}" y="{y + TILE_H / 2}" '
                    f'text-anchor="middle" dominant-baseline="middle">EMPTY</text>'
                )
                continue

            entry_type = str(entry.get("type", ""))
            github_id = str(entry.get("githubId", "-"))
            href = repo_file_url(github_id, entry_type, repo_owner, repo_name, branch)
            title, subtitle, run_id = entry_label(entry)
            css_class = css_class_for_entry(entry_type)

            parts.append(f'<a href="{escape(href)}" target="_blank">')
            parts.append(
                f'<rect class="{css_class}" x="{x}" y="{y}" width="{TILE_W}" height="{TILE_H}" />'
            )
            parts.append(
                f'<text class="tile-title" x="{x + 6}" y="{y + 18}">{escape(title)}</text>'
            )
            parts.append(
                f'<text class="tile-sub" x="{x + 6}" y="{y + 36}">{escape(subtitle)}</text>'
            )
            parts.append(
                f'<text class="tile-run" x="{x + 6}" y="{y + 54}">Run: {escape(run_id)}</text>'
            )
            parts.append(
                f'<text class="tile-run" x="{x + 6}" y="{y + 72}">Tile: ({col},{row})</text>'
            )
            parts.append("</a>")

    parts.append("</svg>")
    return "\n".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate USERS.svg from project/manifest.json"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repo-owner", default=DEFAULT_REPO_OWNER)
    parser.add_argument("--repo-name", default=DEFAULT_REPO_NAME)
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    manifest = load_manifest(args.manifest)
    svg = generate_svg(
        manifest=manifest,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        branch=args.branch,
    )

    args.output.write_text(svg, encoding="utf-8")

    print(f"manifest : {args.manifest}")
    print(f"output   : {args.output}")
    print("DONE")


if __name__ == "__main__":
    main()