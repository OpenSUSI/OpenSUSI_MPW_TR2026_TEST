# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from pathlib import Path
from typing import Optional
import yaml

import klayout.db as pya

from aggregate_manifest import Placement
from aggregate_scan import UserEntry


SYSTEM_TEG_DIRNAME = "000_system"
SYSTEM_FILL_DIRNAME = "000_system"


# ----------------------------
# GDS utilities
# ----------------------------
def get_single_top_cell_name_after_read(layout, before_names, source):
    after_names = {cell.name for cell in layout.top_cells()}
    new_names = sorted(after_names - before_names)

    if len(new_names) != 1:
        raise RuntimeError(f"GDS must add exactly one top cell: {source}, added={new_names}")

    return new_names[0]


def ensure_size_within_pitch(layout, top_name, pitch_x, pitch_y, source):
    cell = layout.cell(top_name)
    box = cell.bbox()
    dbu = layout.dbu

    width = box.width() * dbu
    height = box.height() * dbu

    if width > pitch_x or height > pitch_y:
        raise RuntimeError(
            f"GDS exceeds tile size: {source}, width={width}, height={height}"
        )


def insert_instance(parent, child, x_um, y_um, dbu):
    trans = pya.Trans(pya.Point(int(round(x_um / dbu)), int(round(y_um / dbu))))
    parent.insert(pya.CellInstArray(child.cell_index(), trans))


# ----------------------------
# Logo / XY helpers
# ----------------------------
def load_logo_map(path: Path):
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tiles = data.get("tiles") or {}

    if not isinstance(tiles, dict):
        raise RuntimeError(f"Invalid logo_map format: {path}")

    return tiles


def resolve_logo_path(config, logo_map, row, col):
    key = f"{row},{col}"
    filename = logo_map.get(key, config.logo_default)
    return Path(config.logo_dir) / filename


def get_or_load_logo_cell(layout, logo_path, logo_cache):
    key = str(logo_path)

    if key in logo_cache:
        return logo_cache[key]

    if not logo_path.exists():
        raise RuntimeError(f"Logo GDS not found: {logo_path}")

    before = {c.name for c in layout.top_cells()}
    layout.read(str(logo_path))
    logo_top = get_single_top_cell_name_after_read(layout, before, logo_path)
    logo_cell = layout.cell(logo_top)

    logo_cache[key] = logo_cell
    return logo_cell


def create_xy_text_pcell(layout, text, layer, mag=0.35):
    """
    Basic.TEXT PCell を生成する。
    mag は文字倍率。BBOX 160x110 に収めるため小さめにする。
    """
    lib = pya.Library.library_by_name("Basic")
    if lib is None:
        raise RuntimeError("KLayout Basic library not found")

    layer_info = pya.LayerInfo(layer[0], layer[1])

    # Basic.TEXT PCell
    # KLayout の Basic ライブラリ前提
    cell = layout.create_cell(
        "TEXT",
        "Basic",
        {
            "text": text,
            "layer": layer_info,
            "mag": mag,
        },
    )

    if cell is None:
        raise RuntimeError("Failed to create Basic.TEXT PCell")

    return cell


def build_user_wrapper_cell(
    layout,
    user_cell,
    user_top_name,
    config,
    logo_map,
    row,
    col,
    user,
    logo_cache,
):
    short_id = (user.manifest or {}).get("shortOrderId", "unknown")
    wrapper_name = f"WRAP_{user_top_name}_{short_id}"
    wrapper = layout.create_cell(wrapper_name)

    dbu = layout.dbu

    # ----------------------------
    # USER GDS
    # ----------------------------
    insert_instance(wrapper, user_cell, 0, 0, dbu)

    # ----------------------------
    # LOGO
    # ----------------------------
    logo_path = resolve_logo_path(config, logo_map, row, col)
    logo_cell = get_or_load_logo_cell(layout, logo_path, logo_cache)

    for pos in config.logo_positions:
        insert_instance(wrapper, logo_cell, pos[0], pos[1], dbu)

    # ----------------------------
    # XY (Basic.TEXT PCell)
    # ----------------------------
    xy_text = config.xy_format.format(row=row, col=col)
    xy_cell = create_xy_text_pcell(layout, xy_text, config.xy_layer, mag=0.35)

    insert_instance(wrapper, xy_cell, config.xy_pos[0], config.xy_pos[1], dbu)

    return wrapper


# ----------------------------
# Placement
# ----------------------------
def make_placement(
    *,
    entry_type,
    github_id,
    gds_file,
    top_name,
    x,
    y,
    tile_index,
    row,
    col,
    manifest=None,
):
    manifest = manifest or {}

    return Placement(
        type=entry_type,
        githubId=github_id,
        gdsFile=str(gds_file).replace("\\", "/"),
        gdsTopCell=top_name,
        x=x,
        y=y,
        tileIndex=tile_index,
        row=row,
        col=col,
        paymentSequence=manifest.get("paymentSequence"),
        normalizedRepoName=manifest.get("normalizedRepoName"),
        shortOrderId=manifest.get("shortOrderId"),
        orderId=manifest.get("orderId"),
        sourceRepo=manifest.get("sourceRepo"),
        sourceRunId=manifest.get("sourceRunId"),
        sourceArtifactName=manifest.get("sourceArtifactName"),
    )


# ----------------------------
# GDS load
# ----------------------------
def read_gds_into_layout(layout, gds_path):
    before = {cell.name for cell in layout.top_cells()}
    layout.read(str(gds_path))
    return get_single_top_cell_name_after_read(layout, before, gds_path)


def read_user_gds_into_layout(layout, user):
    top_name = read_gds_into_layout(layout, user.gds)
    expected = (user.manifest or {}).get("gdsTopCell")

    if expected and top_name != expected:
        raise RuntimeError(f"Top mismatch: {expected} vs {top_name}")

    return top_name


# ----------------------------
# Aggregate
# ----------------------------
def aggregate(config, users, positions, out_gds: Path):
    layout = pya.Layout()
    layout.dbu = 0.001

    top = layout.create_cell(config.top_cell)
    logo_map = load_logo_map(config.logo_map_path)
    logo_cache = {}

    placements = []
    start_user_index = 0

    # ----------------------------
    # TEG（LOGO/XYなし）
    # ----------------------------
    if config.teg_gds:
        tile_index, row, col, x, y = positions[0]

        top_name = read_gds_into_layout(layout, config.teg_gds)
        cell = layout.cell(top_name)

        insert_instance(top, cell, x, y, layout.dbu)

        placements.append(
            make_placement(
                entry_type="teg",
                github_id=SYSTEM_TEG_DIRNAME,
                gds_file=config.teg_gds,
                top_name=top_name,
                x=x,
                y=y,
                tile_index=tile_index,
                row=row,
                col=col,
            )
        )

        start_user_index = 1

    # ----------------------------
    # USERS（LOGO + XY）
    # ----------------------------
    for i, user in enumerate(users):
        tile_index, row, col, x, y = positions[start_user_index + i]

        top_name = read_user_gds_into_layout(layout, user)

        ensure_size_within_pitch(
            layout,
            top_name,
            config.pitch_x,
            config.pitch_y,
            user.gds,
        )

        user_cell = layout.cell(top_name)

        wrapper = build_user_wrapper_cell(
            layout,
            user_cell,
            top_name,
            config,
            logo_map,
            row,
            col,
            user,
            logo_cache,
        )

        insert_instance(top, wrapper, x, y, layout.dbu)

        placements.append(
            make_placement(
                entry_type="user",
                github_id=user.github_id,
                gds_file=user.gds,
                top_name=top_name,
                x=x,
                y=y,
                tile_index=tile_index,
                row=row,
                col=col,
                manifest=user.manifest,
            )
        )

    # ----------------------------
    # FILL（LOGOなし）
    # ----------------------------
    fill_start = start_user_index + len(users)
    remain = len(positions) - fill_start

    if remain > 0:
        fill_top = read_gds_into_layout(layout, config.fill_gds)
        fill_cell = layout.cell(fill_top)

        for j in range(remain):
            tile_index, row, col, x, y = positions[fill_start + j]
            insert_instance(top, fill_cell, x, y, layout.dbu)

            placements.append(
                make_placement(
                    entry_type="fill",
                    github_id=SYSTEM_FILL_DIRNAME,
                    gds_file=config.fill_gds,
                    top_name=fill_top,
                    x=x,
                    y=y,
                    tile_index=tile_index,
                    row=row,
                    col=col,
                )
            )

    out_gds.parent.mkdir(parents=True, exist_ok=True)
    layout.write(str(out_gds))

    return placements