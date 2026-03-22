# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
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


def parse_xy(xy: str) -> Tuple[int, int]:
    text = str(xy).strip().lower()
    parts = text.split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid aggregate.xy format: {xy}")
    return int(parts[0]), int(parts[1])


def load_config(path: Path) -> AggregateConfig:
    if not path.exists():
        raise FileNotFoundError(f"info.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    agg = data.get("aggregate") or {}

    if "top_cell" not in agg:
        raise KeyError("aggregate.top_cell is missing")
    if "pitch_x" not in agg:
        raise KeyError("aggregate.pitch_x is missing")
    if "pitch_y" not in agg:
        raise KeyError("aggregate.pitch_y is missing")
    if "xy" not in agg:
        raise KeyError("aggregate.xy is missing")

    gx, gy = parse_xy(agg["xy"])

    teg_gds = Path(agg["teg_gds"]) if agg.get("teg_gds") else None
    fill_gds = Path(agg["fillgds"]) if agg.get("fillgds") else None

    return AggregateConfig(
        top_cell=str(agg["top_cell"]).strip(),
        pitch_x=float(agg["pitch_x"]),
        pitch_y=float(agg["pitch_y"]),
        grid_x=gx,
        grid_y=gy,
        teg_gds=teg_gds,
        fill_gds=fill_gds,
    )