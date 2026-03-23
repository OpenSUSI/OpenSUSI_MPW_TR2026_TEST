# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
from pathlib import Path
from typing import Optional
import klayout.db as pya

from aggregate_manifest import Placement
from aggregate_scan import UserEntry


SYSTEM_TEG_DIRNAME = "000_system"
SYSTEM_FILL_DIRNAME = "000_system"


def get_top_cells(layout: pya.Layout) -> list[pya.Cell]:
    return list(layout.top_cells())


def get_single_top_cell_name_after_read(layout: pya.Layout, before_names: set[str], source: Path) -> str:
    after_names = {cell.name for cell in get_top_cells(layout)}
    new_names = sorted(after_names - before_names)

    if len(new_names) != 1:
        raise RuntimeError(
            f"GDS must add exactly one top cell when read: {source}, added={new_names}"
        )

    return new_names[0]


def load_single_top_bbox(layout: pya.Layout, top_name: str) -> dict[str, float]:
    cell = layout.cell(top_name)
    if cell is None:
        raise RuntimeError(f"Cell not found after read: {top_name}")

    box = cell.bbox()
    dbu = layout.dbu

    return {
        "left": box.left * dbu,
        "bottom": box.bottom * dbu,
        "right": box.right * dbu,
        "top": box.top * dbu,
        "width": box.width() * dbu,
        "height": box.height() * dbu,
    }


def ensure_size_within_pitch(layout: pya.Layout, top_name: str, pitch_x: float, pitch_y: float, source: Path) -> None:
    bbox = load_single_top_bbox(layout, top_name)
    if bbox["width"] > pitch_x or bbox["height"] > pitch_y:
        raise RuntimeError(
            f"GDS exceeds tile size: {source}, "
            f"width={bbox['width']}, height={bbox['height']}, pitch=({pitch_x}, {pitch_y})"
        )


def insert_instance(parent: pya.Cell, child: pya.Cell, x_um: float, y_um: float, dbu: float) -> None:
    trans = pya.Trans(pya.Point(int(round(x_um / dbu)), int(round(y_um / dbu))))
    parent.insert(pya.CellInstArray(child.cell_index(), trans))


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
        orderId=manifest.get("orderId"),
        sourceRepo=manifest.get("sourceRepo"),
        sourceRunId=manifest.get("sourceRunId"),
        sourceArtifactName=manifest.get("sourceArtifactName"),
    )


def read_gds_into_layout(layout: pya.Layout, gds_path: Path) -> str:
    if not gds_path.exists():
        raise FileNotFoundError(f"GDS not found: {gds_path}")

    before_names = {cell.name for cell in get_top_cells(layout)}
    layout.read(str(gds_path))
    top_name = get_single_top_cell_name_after_read(layout, before_names, gds_path)
    return top_name


def aggregate(config, users: list[UserEntry], positions, out_gds: Path):
    max_tiles = config.grid_x * config.grid_y

    # TEG uses one tile if present
    teg_slots = 1 if config.teg_gds else 0
    available_user_slots = max_tiles - teg_slots

    if len(users) > available_user_slots:
        raise RuntimeError(
            f"Too many users: {len(users)} > available user slots {available_user_slots}"
        )

    if len(users) < available_user_slots and not config.fill_gds:
        raise RuntimeError("fillgds is required when user count is less than remaining grid capacity")

    if config.teg_gds and not config.teg_gds.exists():
        raise FileNotFoundError(f"TEG GDS not found: {config.teg_gds}")

    if config.fill_gds and not config.fill_gds.exists():
        raise FileNotFoundError(f"Fill GDS not found: {config.fill_gds}")

    layout = pya.Layout()
    layout.dbu = 0.001
    top = layout.create_cell(config.top_cell)
    placements: list[Placement] = []

    # ----------------------------
    # 1. TEG at tile position (0,0) => positions[0]
    # ----------------------------
    start_user_index = 0

    if config.teg_gds:
        teg_tile_index, teg_row, teg_col, teg_x, teg_y = positions[0]

        top_name = read_gds_into_layout(layout, config.teg_gds)
        teg_cell = layout.cell(top_name)

        if teg_cell is None:
            raise RuntimeError(f"Failed to load TEG top cell: {top_name}")

        ensure_size_within_pitch(layout, top_name, config.pitch_x, config.pitch_y, config.teg_gds)
        insert_instance(top, teg_cell, teg_x, teg_y, layout.dbu)

        placements.append(
            make_placement(
                entry_type="teg",
                github_id=SYSTEM_TEG_DIRNAME,
                gds_file=config.teg_gds,
                top_name=top_name,
                x=teg_x,
                y=teg_y,
                tile_index=teg_tile_index,
                row=teg_row,
                col=teg_col,
                manifest=None,
            )
        )

        start_user_index = 1

    # ----------------------------
    # 2. Users start from positions[start_user_index]
    # ----------------------------
    for i, user in enumerate(users):
        tile_index, row, col, x, y = positions[start_user_index + i]

        top_name = read_gds_into_layout(layout, user.gds)
        user_cell = layout.cell(top_name)

        if user_cell is None:
            raise RuntimeError(f"Failed to load user top cell: {top_name}")

        ensure_size_within_pitch(layout, top_name, config.pitch_x, config.pitch_y, user.gds)
        insert_instance(top, user_cell, x, y, layout.dbu)

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
    # 3. Fill remaining slots
    # ----------------------------
    fill_start = start_user_index + len(users)
    remain = max_tiles - fill_start

    if remain > 0:
        if not config.fill_gds:
            raise RuntimeError("fillgds is required for remaining slots")

        fill_top_name = read_gds_into_layout(layout, config.fill_gds)
        fill_cell = layout.cell(fill_top_name)

        if fill_cell is None:
            raise RuntimeError(f"Failed to load fill top cell: {fill_top_name}")

        ensure_size_within_pitch(layout, fill_top_name, config.pitch_x, config.pitch_y, config.fill_gds)

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
                    manifest=None,
                )
            )

    out_gds.parent.mkdir(parents=True, exist_ok=True)
    layout.write(str(out_gds))

    return placements