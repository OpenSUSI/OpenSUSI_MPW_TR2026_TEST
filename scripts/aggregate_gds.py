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


SYSTEM_TEG_DIRNAME  = "00_system"
SYSTEM_FILL_DIRNAME = "000_system"

def load_layout(path: Path) -> pya.Layout:
    if not path.exists():
        raise FileNotFoundError(f"GDS not found: {path}")

    layout = pya.Layout()
    layout.read(str(path))
    return layout


def get_single_top(layout: pya.Layout, source: Path) -> pya.Cell:
    top_cells = list(layout.top_cells())

    if len(top_cells) != 1:
        names = [c.name for c in top_cells]
        raise RuntimeError(f"GDS must have exactly one top cell: {source}, tops={names}")

    return top_cells[0]


def bbox_um(cell: pya.Cell, dbu: float) -> dict[str, float]:
    box = cell.bbox()
    return {
        "left": box.left * dbu,
        "bottom": box.bottom * dbu,
        "right": box.right * dbu,
        "top": box.top * dbu,
        "width": box.width() * dbu,
        "height": box.height() * dbu,
    }


def ensure_size_within_pitch(cell: pya.Cell, dbu: float, pitch_x: float, pitch_y: float, source: Path) -> None:
    b = bbox_um(cell, dbu)
    if b["width"] > pitch_x or b["height"] > pitch_y:
        raise RuntimeError(
            f"GDS exceeds tile size: {source}, "
            f"width={b['width']}, height={b['height']}, pitch=({pitch_x}, {pitch_y})"
        )


def insert_instance(parent: pya.Cell, child: pya.Cell, x_um: float, y_um: float, dbu: float) -> None:
    trans = pya.Trans(pya.Point(int(round(x_um / dbu)), int(round(y_um / dbu))))
    parent.insert(pya.CellInstArray(child.cell_index(), trans))


def copy_layout_tree(target_layout: pya.Layout, source_layout: pya.Layout) -> None:
    cell_mapping = pya.CellMapping()
    target_layout.copy_tree_shapes(source_layout, cell_mapping)


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


def aggregate(config, users: list[UserEntry], positions, out_gds: Path):
    max_tiles = config.grid_x * config.grid_y
    if len(users) > max_tiles:
        raise RuntimeError(f"Too many users: {len(users)} > {max_tiles}")

    if len(users) < max_tiles and not config.fill_gds:
        raise RuntimeError("fillgds is required when user count is less than grid capacity")

    if config.teg_gds and not config.teg_gds.exists():
        raise FileNotFoundError(f"TEG GDS not found: {config.teg_gds}")

    if config.fill_gds and not config.fill_gds.exists():
        raise FileNotFoundError(f"Fill GDS not found: {config.fill_gds}")

    layout = pya.Layout()
    top = layout.create_cell(config.top_cell)
    placements: list[Placement] = []

    dbu: Optional[float] = None

    # TEG at origin
    if config.teg_gds:
        teg_layout = load_layout(config.teg_gds)
        teg_top = get_single_top(teg_layout, config.teg_gds)

        dbu = teg_layout.dbu
        layout.dbu = dbu

        copy_layout_tree(layout, teg_layout)
        copied_teg = layout.cell(teg_top.name)
        if copied_teg is None:
            raise RuntimeError(f"Failed to copy TEG top cell: {teg_top.name}")

        insert_instance(top, copied_teg, 0.0, 0.0, dbu)

        placements.append(
            make_placement(
                entry_type="teg",
                github_id=SYSTEM_TEG_DIRNAME,
                gds_file=config.teg_gds,
                top_name=copied_teg.name,
                x=0.0,
                y=0.0,
                tile_index=-1,
                row=None,
                col=None,
                manifest=None,
            )
        )

    # Users
    for i, user in enumerate(users):
        tile_index, row, col, x, y = positions[i]

        user_layout = load_layout(user.gds)

        if dbu is None:
            dbu = user_layout.dbu
            layout.dbu = dbu

        if abs(user_layout.dbu - dbu) > 1e-12:
            raise RuntimeError(f"DBU mismatch: aggregate={dbu}, user={user_layout.dbu}, file={user.gds}")

        user_top = get_single_top(user_layout, user.gds)
        ensure_size_within_pitch(user_top, user_layout.dbu, config.pitch_x, config.pitch_y, user.gds)

        copy_layout_tree(layout, user_layout)
        copied_user = layout.cell(user_top.name)
        if copied_user is None:
            raise RuntimeError(f"Failed to copy user top cell: {user_top.name}")

        insert_instance(top, copied_user, x, y, dbu)

        placements.append(
            make_placement(
                entry_type="user",
                github_id=user.github_id,
                gds_file=user.gds,
                top_name=copied_user.name,
                x=x,
                y=y,
                tile_index=tile_index,
                row=row,
                col=col,
                manifest=user.manifest,
            )
        )

    # Fill
    remain = len(positions) - len(users)
    if remain > 0:
        fill_layout = load_layout(config.fill_gds)

        if dbu is None:
            dbu = fill_layout.dbu
            layout.dbu = dbu

        if abs(fill_layout.dbu - dbu) > 1e-12:
            raise RuntimeError(f"DBU mismatch: aggregate={dbu}, fill={fill_layout.dbu}, file={config.fill_gds}")

        fill_top = get_single_top(fill_layout, config.fill_gds)
        ensure_size_within_pitch(fill_top, fill_layout.dbu, config.pitch_x, config.pitch_y, config.fill_gds)

        copy_layout_tree(layout, fill_layout)
        copied_fill = layout.cell(fill_top.name)
        if copied_fill is None:
            raise RuntimeError(f"Failed to copy fill top cell: {fill_top.name}")

        for j in range(remain):
            tile_index, row, col, x, y = positions[len(users) + j]

            insert_instance(top, copied_fill, x, y, dbu)

            placements.append(
                make_placement(
                    entry_type="fill",
                    github_id=SYSTEM_FILL_DIRNAME,
                    gds_file=config.fill_gds,
                    top_name=copied_fill.name,
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