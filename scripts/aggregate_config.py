# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class AggregateConfig:
    top_cell: str
    pitch_x: float
    pitch_y: float
    grid_x: int
    grid_y: int
    teg_gds: Optional[Path]
    fill_gds: Optional[Path]


def parse_xy(value: str) -> tuple[int, int]:
    text = str(value).strip().lower()
    parts = text.split("x")

    if len(parts) != 2:
        raise ValueError(f"Invalid aggregate.xy format: {value}")

    return int(parts[0]), int(parts[1])


def load_config(path: Path) -> AggregateConfig:
    if not path.exists():
        raise FileNotFoundError(f"info.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agg = data.get("aggregate") or {}

    required = ["top_cell", "pitch_x", "pitch_y", "xy"]
    missing = [key for key in required if key not in agg]
    if missing:
        raise KeyError(f"Missing aggregate config keys: {', '.join(missing)}")

    top_cell = str(agg["top_cell"]).strip()
    if not top_cell:
        raise ValueError("aggregate.top_cell must not be empty")

    grid_x, grid_y = parse_xy(agg["xy"])

    teg_gds = Path(agg["teg_gds"]) if agg.get("teg_gds") else None
    fill_gds = Path(agg["fillgds"]) if agg.get("fillgds") else None

    return AggregateConfig(
        top_cell=top_cell,
        pitch_x=float(agg["pitch_x"]),
        pitch_y=float(agg["pitch_y"]),
        grid_x=grid_x,
        grid_y=grid_y,
        teg_gds=teg_gds,
        fill_gds=fill_gds,
    )