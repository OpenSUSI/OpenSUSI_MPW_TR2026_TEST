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

    logo_dir: Path
    logo_default: str
    logo_positions: list[tuple[float, float]]

    xy_layer: tuple[int, int]
    xy_bbox: tuple[float, float]
    xy_pos: tuple[float, float]
    xy_format: str
    xy_text_gds: Path

    logo_map_path: Path


def require_section(data: dict, key: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise KeyError(f"Missing or invalid section: {key}")
    return value


def require_string(data: dict, key: str, section: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise KeyError(f"Missing required key: {section}.{key}")
    return value


def require_float(data: dict, key: str, section: str) -> float:
    if key not in data:
        raise KeyError(f"Missing required key: {section}.{key}")
    return float(data[key])


def require_int(data: dict, key: str, section: str) -> int:
    if key not in data:
        raise KeyError(f"Missing required key: {section}.{key}")
    return int(data[key])


def require_xy_pair(data: dict, section: str) -> tuple[float, float]:
    if not isinstance(data, dict):
        raise KeyError(f"Missing or invalid section: {section}")

    if "x" not in data or "y" not in data:
        raise KeyError(f"Missing required keys: {section}.x / {section}.y")

    return float(data["x"]), float(data["y"])


def require_layer_pair(value, section: str) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{section} must be [layer, datatype]")

    return int(value[0]), int(value[1])


def load_config(path: Path) -> AggregateConfig:
    if not path.exists():
        raise FileNotFoundError(f"info.yaml not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    aggregate = require_section(data, "aggregate")
    logo = require_section(data, "logo")
    xy_mark = require_section(data, "xy_mark")

    aggregate_pitch = require_section(aggregate, "pitch")
    aggregate_grid = require_section(aggregate, "grid")

    logo_placements = require_section(logo, "placements")
    xy_placement = require_section(xy_mark, "placement")
    xy_bbox = require_section(xy_mark, "bbox")

    top_cell = require_string(aggregate, "top_cell", "aggregate")
    pitch_x = require_float(aggregate_pitch, "x", "aggregate.pitch")
    pitch_y = require_float(aggregate_pitch, "y", "aggregate.pitch")
    grid_x = require_int(aggregate_grid, "x", "aggregate.grid")
    grid_y = require_int(aggregate_grid, "y", "aggregate.grid")

    teg_gds = Path(aggregate["teg_gds"]) if aggregate.get("teg_gds") else None
    fill_gds = Path(aggregate["fill_gds"]) if aggregate.get("fill_gds") else None

    logo_dir = Path(require_string(logo, "dir", "logo"))
    logo_default = require_string(logo, "default", "logo")

    top_left = require_xy_pair(
        logo_placements["top_left"],
        "logo.placements.top_left",
    )
    top_right = require_xy_pair(
        logo_placements["top_right"],
        "logo.placements.top_right",
    )
    bottom_right = require_xy_pair(
        logo_placements["bottom_right"],
        "logo.placements.bottom_right",
    )
    logo_positions = [top_left, top_right, bottom_right]

    xy_layer = require_layer_pair(xy_mark.get("layer"), "xy_mark.layer")
    xy_bbox_pair = require_xy_pair(xy_bbox, "xy_mark.bbox")
    xy_pos = require_xy_pair(xy_placement, "xy_mark.placement")
    xy_format = str(xy_mark.get("format", "X{col}Y{row}")).strip() or "X{col}Y{row}"
    xy_text_gds = Path(require_string(xy_mark, "text_gds", "xy_mark"))

    logo_map_path = Path(
        str(data.get("logo_map", "logo_map.yaml")).strip() or "logo_map.yaml"
    )

    return AggregateConfig(
        top_cell=top_cell,
        pitch_x=pitch_x,
        pitch_y=pitch_y,
        grid_x=grid_x,
        grid_y=grid_y,
        teg_gds=teg_gds,
        fill_gds=fill_gds,
        logo_dir=logo_dir,
        logo_default=logo_default,
        logo_positions=logo_positions,
        xy_layer=xy_layer,
        xy_bbox=xy_bbox_pair,
        xy_pos=xy_pos,
        xy_format=xy_format,
        xy_text_gds=xy_text_gds,
        logo_map_path=logo_map_path,
    )