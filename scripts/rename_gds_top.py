#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----

import argparse
import re
from pathlib import Path

import klayout.db as pya

MAX_GDS_CELL_NAME_LEN = 64


def normalize_name(value: str) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def extract_repo_name(source_repo: str) -> str:
    value = str(source_repo or "").strip()
    parts = value.split("/")
    if len(parts) >= 2 and parts[-1]:
        return parts[-1]
    return value or "unknown"


def order_id_to_short_id(order_id: str) -> str:
    safe = str(order_id or "").strip()

    m = re.match(r"^ORD-20(\d{2})(\d{2})(\d{2})-(.+)$", safe)
    if m:
        return f"ORD-{m.group(1)}{m.group(2)}{m.group(3)}-{m.group(4)}"

    return safe


def build_top_cell_name(
    github_id: str,
    source_repo: str,
    order_id: str,
    slot_id: str
) -> str:
    gid = normalize_name(github_id)
    repo = normalize_name(extract_repo_name(source_repo))
    short_order = normalize_name(order_id_to_short_id(order_id))
    slot = normalize_name(slot_id)

    name = f"tr_1um_{gid}_{repo}_{short_order}_{slot}"
    return name[:MAX_GDS_CELL_NAME_LEN]


def get_single_top_cell(layout: pya.Layout, source: Path) -> pya.Cell:
    tops = list(layout.top_cells())
    if len(tops) != 1:
        names = [cell.name for cell in tops]
        raise RuntimeError(
            f"GDS must have exactly one top cell: {source}, top_cells={names}"
        )
    return tops[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename top cell in GDSII to OpenSUSI naming rule."
    )
    parser.add_argument("--gds", type=Path, required=True)
    parser.add_argument("--github-id", required=True)
    parser.add_argument("--source-repo", required=True)

    # New MPW naming inputs.
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--slot-id", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.gds.exists():
        raise FileNotFoundError(f"GDS not found: {args.gds}")

    layout = pya.Layout()
    layout.read(str(args.gds))

    top = get_single_top_cell(layout, args.gds)
    new_name = build_top_cell_name(
        args.github_id,
        args.source_repo,
        args.order_id,
        args.slot_id
    )

    old_name = top.name
    if old_name != new_name:
        print(f"rename top cell: {old_name} -> {new_name}")
        top.name = new_name
        layout.write(str(args.gds))
    else:
        print(f"top cell already matches: {new_name}")


if __name__ == "__main__":
    main()