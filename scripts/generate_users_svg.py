#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
import argparse
import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any


DEFAULT_MANIFEST = Path("project/manifest.json")
DEFAULT_OUTPUT = Path("USERS.svg")

TILE_W = 140
TILE_H = 90
MARGIN = 30
HEADER_H = 40
ROW_LABEL_W = 30


def normalize_string(value: Any) -> str:
    return str(value or "").strip()


def normalize_int(value: Any) -> int:
    text = normalize_string(value)
    return int(text) if text else 0


def order_id_to_dir_name(order_id: Any) -> str:
    value = normalize_string(order_id)
    match = re.fullmatch(r"ORD-20([0-9]{2})([0-9]{2})([0-9]{2})-(.+)", value)

    if not match:
        return value

    yy, mm, dd, suffix = match.groups()
    return f"ORD-{yy}{mm}{dd}-{suffix}"


def get_default_repo_owner() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        return repo.split("/", 1)[0]
    return "OpenSUSI"


def get_default_repo_name() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        return repo.split("/", 1)[1]
    return "OpenSUSI_MPW_TR2026"


def get_default_branch() -> str:
    return os.environ.get("GITHUB_REF_NAME", "main")


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def filter_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        entry
        for entry in manifest.get("entries", [])
        if entry.get("type") in {"teg", "user", "fill"}
    ]


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        entries,
        key=lambda e: (
            e.get("row", 9999) if e.get("row") is not None else 9999,
            e.get("col", 9999) if e.get("col") is not None else 9999,
        ),
    )


def repo_file_url(
    entry: dict[str, Any],
    repo_owner: str,
    repo_name: str,
    branch: str,
) -> str:
    entry_type = entry.get("type", "")
    github_id = entry.get("githubId", "-")

    if entry_type in {"teg", "fill"}:
        rel = "users/000_system"
    else:
        order_dir = order_id_to_dir_name(entry.get("orderId"))
        slot = f"{normalize_int(entry.get('submissionSequence')):02d}"
        rel = f"users/{github_id}/{order_dir}/{slot}"

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
        title = "EMPTY"
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

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        """<style>
text { font-family: Arial, sans-serif; fill: black; }
.tile { fill: white; stroke: black; stroke-width: 1; }
.tile-teg { fill: #cdd6c1; }
.tile-user { fill: #ffe8f4; }
.tile-fill { fill: #f7f7f7; }
.grid-label { font-size: 12px; }
.title { font-size: 18px; font-weight: bold; }
.tile-title { font-size: 13px; font-weight: bold; }
.tile-sub { font-size: 11px; }
.tile-run { font-size: 10px; }
</style>""",
        f'<text class="title" x="{MARGIN}" y="{MARGIN}">OpenSUSI MPW Users Layout</text>',
    ]

    for col in range(grid_x):
        x, _ = tile_screen_xy(col, 0)
        parts.append(
            f'<text class="grid-label" x="{x + TILE_W / 2}" y="{HEADER_H + 15}" '
            f'text-anchor="middle">{col}</text>'
        )

    for row in range(grid_y):
        _, y = tile_screen_xy(0, row)
        parts.append(
            f'<text class="grid-label" x="{ROW_LABEL_W + MARGIN - 10}" y="{y + TILE_H / 2}" '
            f'text-anchor="end" dominant-baseline="middle">{row}</text>'
        )

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
            href = repo_file_url(entry, repo_owner, repo_name, branch)
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
    parser.add_argument("--repo-owner", default=get_default_repo_owner())
    parser.add_argument("--repo-name", default=get_default_repo_name())
    parser.add_argument("--branch", default=get_default_branch())
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
    print(f"repo     : {args.repo_owner}/{args.repo_name}")
    print(f"branch   : {args.branch}")
    print("DONE")


if __name__ == "__main__":
    main()