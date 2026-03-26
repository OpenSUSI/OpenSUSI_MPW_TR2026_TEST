# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from pathlib import Path
from typing import Optional

import klayout.db as pya

from aggregate_manifest import Placement
from aggregate_scan import UserEntry


SYSTEM_TEG_DIRNAME = "000_system"
SYSTEM_FILL_DIRNAME = "000_system"


# ----------------------------
# GDS utilities
# ----------------------------
def get_single_top_cell_name_after_read(
    layout: pya.Layout, before_names: set[str], source: Path
) -> str:
    after_names = {cell.name for cell in layout.top_cells()}
    new_names = sorted(after_names - before_names)

    if len(new_names) != 1:
        raise RuntimeError(
            f"GDS must add exactly one top cell: {source}, added={new_names}"
        )

    return new_names[0]


def ensure_size_within_pitch(
    layout: pya.Layout,
    top_name: str,
    pitch_x: float,
    pitch_y: float,
    source: Path,
) -> None:
    cell = layout.cell(top_name)
    if cell is None:
        raise RuntimeError(f"Cell not found: {top_name}")

    box = cell.bbox()
    dbu = layout.dbu

    width = box.width() * dbu
    height = box.height() * dbu

    if width > pitch_x or height > pitch_y:
        raise RuntimeError(
            f"GDS exceeds tile size: {source}, "
            f"width={width}, height={height}, pitch=({pitch_x}, {pitch_y})"
        )


def insert_instance(
    parent: pya.Cell,
    child: pya.Cell,
    x_um: float,
    y_um: float,
    dbu: float,
) -> None:
    trans = pya.Trans(pya.Point(int(round(x_um / dbu)), int(round(y_um / dbu))))
    parent.insert(pya.CellInstArray(child.cell_index(), trans))


# ----------------------------
# Placement
# ----------------------------
def make_placement(
    *,
    entry_type: str,
    github_id: str,
    gds_file: Path,
    top_name: str,
    x: float,
    y: float,
    tile_index: int,
    row: Optional[int],
    col: Optional[int],
    manifest: Optional[dict] = None,
) -> Placement:
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
def read_gds_into_layout(layout: pya.Layout, gds_path: Path) -> str:
    if not gds_path.exists():
        raise FileNotFoundError(f"GDS not found: {gds_path}")

    before = {cell.name for cell in layout.top_cells()}
    layout.read(str(gds_path))
    return get_single_top_cell_name_after_read(layout, before, gds_path)


def read_user_gds_into_layout(layout: pya.Layout, user: UserEntry) -> str:
    top_name = read_gds_into_layout(layout, user.gds)

    expected = (user.manifest or {}).get("gdsTopCell")
    if expected and top_name != expected:
        raise RuntimeError(
            f"Top cell mismatch: expected={expected}, got={top_name}, source={user.gds}"
        )

    return top_name


# ----------------------------
# Aggregate
# ----------------------------
def aggregate(config, users: list[UserEntry], positions, out_gds: Path):
    max_tiles = config.grid_x * config.grid_y
    teg_slots = 1 if config.teg_gds else 0
    available_user_slots = max_tiles - teg_slots

    if len(users) > available_user_slots:
        raise RuntimeError(
            f"Too many users: {len(users)} > {available_user_slots}"
        )

    if len(users) < available_user_slots and not config.fill_gds:
        raise RuntimeError("fillgds is required")

    layout = pya.Layout()
    layout.dbu = 0.001
    top = layout.create_cell(config.top_cell)

    placements: list[Placement] = []
    start_user_index = 0

    # ----------------------------
    # TEG
    # ----------------------------
    if config.teg_gds:
        tile_index, row, col, x, y = positions[0]

        top_name = read_gds_into_layout(layout, config.teg_gds)
        cell = layout.cell(top_name)

        ensure_size_within_pitch(
            layout, top_name, config.pitch_x, config.pitch_y, config.teg_gds
        )

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
    # USERS
    # ----------------------------
    for i, user in enumerate(users):
        tile_index, row, col, x, y = positions[start_user_index + i]

        top_name = read_user_gds_into_layout(layout, user)
        cell = layout.cell(top_name)

        ensure_size_within_pitch(
            layout, top_name, config.pitch_x, config.pitch_y, user.gds
        )

        insert_instance(top, cell, x, y, layout.dbu)

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
    # FILL
    # ----------------------------
    fill_start = start_user_index + len(users)
    remain = max_tiles - fill_start

    if remain > 0:
        if not config.fill_gds:
            raise RuntimeError("fillgds is required")

        fill_top_name = read_gds_into_layout(layout, config.fill_gds)
        fill_cell = layout.cell(fill_top_name)

        ensure_size_within_pitch(
            layout, fill_top_name, config.pitch_x, config.pitch_y, config.fill_gds
        )

        for j in range(remain):
            tile_index, row, col, x, y = positions[fill_start + j]

            insert_instance(top, fill_cell, x, y, layout.dbu)

            placements.append(
                make_placement(
                    entry_type="fill",
                    github_id=SYSTEM_FILL_DIRNAME,
                    gds_file=config.fill_gds,
                    top_name=fill_top_name,
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