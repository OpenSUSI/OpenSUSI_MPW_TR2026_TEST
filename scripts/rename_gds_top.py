#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pya


def normalize_string(value: object) -> str:
    return str(value or "").strip()


def sanitize_cell_name(value: str) -> str:
    """
    Convert an orderId into a valid and readable GDS cell name.

    Example:
      ORD-260507-104500-01
        -> ORD_260507_104500_01
    """
    raw = normalize_string(value)
    raw = re.sub(r"[^A-Za-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw)
    raw = raw.strip("_")

    if not raw:
        raise ValueError("Cell name is empty after sanitization.")

    if raw[0].isdigit():
        raw = f"CELL_{raw}"

    return raw


def build_top_cell_name(order_id: str) -> str:
    return sanitize_cell_name(order_id)


def rename_gds_top(gds_path: Path, new_top_name: str) -> None:
    if not gds_path.exists():
        raise FileNotFoundError(f"GDS not found: {gds_path}")

    layout = pya.Layout()
    layout.read(str(gds_path))

    top_cells = layout.top_cells()

    if len(top_cells) != 1:
        names = [cell.name for cell in top_cells]
        raise RuntimeError(
            f"Expected exactly one top cell, found {len(top_cells)}: {names}"
        )

    top_cell = top_cells[0]
    old_top_name = top_cell.name

    if old_top_name == new_top_name:
        print(f"Top cell already named '{new_top_name}'. No rename needed.")
    else:
        print(f"Renaming top cell: '{old_top_name}' -> '{new_top_name}'")
        top_cell.name = new_top_name

    layout.write(str(gds_path))

    print(f"Updated GDS: {gds_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename imported GDS top cell using MPW orderId."
    )

    parser.add_argument(
        "--gds",
        required=True,
        help="Path to GDS file to update.",
    )

    parser.add_argument(
        "--order-id",
        required=True,
        help="Full MPW order ID. Example: ORD-260507-104500-01",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    gds_path = Path(args.gds)
    new_top_name = build_top_cell_name(args.order_id)

    rename_gds_top(gds_path, new_top_name)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)