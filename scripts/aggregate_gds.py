# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from pathlib import Path
from typing import Any, Optional

import yaml
import klayout.db as pya

from aggregate_manifest import Placement
from aggregate_scan import UserEntry


SYSTEM_TEG_DIRNAME = "000_system"
SYSTEM_FILL_DIRNAME = "000_system"

ASCII_CELL_PREFIX = "ASCII_"
XY_CHAR_SPACE_UM = 2.0
XY_ALLOWED_SCALES = (1, 2, 3)


# ----------------------------
# Generic utilities
# ----------------------------
def normalize_string(value: Any) -> str:
    return str(value or "").strip()


def normalize_int(value: Any) -> Optional[int]:
    text = normalize_string(value)
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def get_all_cell_names(layout: pya.Layout) -> set[str]:
    names: set[str] = set()

    for index in range(layout.cells()):
        cell = layout.cell(index)
        if cell is None:
            continue

        name = normalize_string(cell.name)
        if name:
            names.add(name)

    return names


# ----------------------------
# GDS utilities
# ----------------------------
def get_single_top_cell_name_after_read(
    layout: pya.Layout,
    before_names: set[str],
    source: Path,
) -> str:
    after_names = {cell.name for cell in layout.top_cells()}
    new_names = sorted(after_names - before_names)

    if len(new_names) != 1:
        raise RuntimeError(
            f"GDS must add exactly one top cell: {source}, added={new_names}"
        )

    return new_names[0]


def read_gds_into_layout(layout: pya.Layout, gds_path: Path) -> str:
    if not gds_path.exists():
        raise FileNotFoundError(f"GDS not found: {gds_path}")

    before = {cell.name for cell in layout.top_cells()}
    layout.read(str(gds_path))
    return get_single_top_cell_name_after_read(layout, before, gds_path)


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
            f"GDS exceeds tile size: {source}, width={width}, height={height}"
        )


def ensure_bbox_within_limit(
    layout: pya.Layout,
    cell: pya.Cell,
    limit_x_um: float,
    limit_y_um: float,
    source_name: str,
) -> None:
    box = cell.bbox()
    dbu = layout.dbu

    width = box.width() * dbu
    height = box.height() * dbu

    if width > limit_x_um or height > limit_y_um:
        raise RuntimeError(
            f"Cell exceeds bbox limit: {source_name}, "
            f"width={width}, height={height}, "
            f"limit=({limit_x_um}, {limit_y_um})"
        )


def insert_instance(
    parent: pya.Cell,
    child: pya.Cell,
    x_um: float,
    y_um: float,
    dbu: float,
) -> None:
    trans = pya.Trans(
        pya.Point(
            int(round(x_um / dbu)),
            int(round(y_um / dbu)),
        )
    )
    parent.insert(pya.CellInstArray(child.cell_index(), trans))


# ----------------------------
# Text helpers
# ----------------------------
def get_text_width_um(
    layout: pya.Layout,
    ascii_cells: dict[str, pya.Cell],
    text: str,
    char_space_um: float = XY_CHAR_SPACE_UM,
) -> float:
    dbu = layout.dbu
    width = 0.0

    for index, ch in enumerate(text):
        glyph = ascii_cells[ch]
        box = glyph.bbox()
        width += box.width() * dbu

        if index != len(text) - 1:
            width += char_space_um

    return width


# ----------------------------
# Logo helpers
# ----------------------------
def load_logo_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    tiles = data.get("tiles") or {}

    if not isinstance(tiles, dict):
        raise RuntimeError(f"Invalid logo_map format: {path}")

    normalized: dict[str, str] = {}
    for key, value in tiles.items():
        map_key = normalize_string(key)
        file_name = normalize_string(value)
        if map_key and file_name:
            normalized[map_key] = file_name

    return normalized


def get_tile_number(user: Any, tile_index: int) -> int:
    """
    logo_map.yaml の tile番号として使う値。
    paymentSequence を優先し、無ければ tile_index を使う。
    """
    manifest = getattr(user, "manifest", None) or {}
    payment_sequence = normalize_int(manifest.get("paymentSequence"))
    if payment_sequence is not None:
        return payment_sequence
    return int(tile_index)


def resolve_logo_path_for_position(
    config,
    logo_map: dict[str, str],
    tile_number: int,
    position_number: int,
) -> Path:
    key = f"{tile_number},{position_number}"
    filename = normalize_string(logo_map.get(key)) or normalize_string(config.logo_default)
    return Path(config.logo_dir) / filename


def get_or_load_logo_cell(
    layout: pya.Layout,
    logo_path: Path,
    logo_cache: dict[str, pya.Cell],
    config,
) -> pya.Cell:
    key = str(logo_path)

    if key in logo_cache:
        return logo_cache[key]

    top_name = read_gds_into_layout(layout, logo_path)
    logo_cell = layout.cell(top_name)

    if logo_cell is None:
        raise RuntimeError(f"Logo top cell not found after read: {logo_path}")

    if hasattr(config, "logo_bbox"):
        limit_x_um, limit_y_um = config.logo_bbox
        ensure_bbox_within_limit(
            layout,
            logo_cell,
            limit_x_um,
            limit_y_um,
            f"logo:{logo_path}",
        )

    logo_cache[key] = logo_cell
    return logo_cell


# ----------------------------
# ASCII glyph helpers
# ----------------------------
def get_or_load_ascii_cells(
    layout: pya.Layout,
    text_gds_path: Path,
    text_cache: dict[str, dict[str, pya.Cell]],
) -> dict[str, pya.Cell]:
    key = str(text_gds_path)

    if key in text_cache:
        return text_cache[key]

    if not text_gds_path.exists():
        raise RuntimeError(f"TEXT GDS not found: {text_gds_path}")

    before_names = get_all_cell_names(layout)
    layout.read(str(text_gds_path))
    after_names = get_all_cell_names(layout)

    new_names = after_names - before_names
    ascii_cells: dict[str, pya.Cell] = {}

    for index in range(layout.cells()):
        cell = layout.cell(index)
        if cell is None:
            continue

        name = normalize_string(cell.name)
        if not name.startswith(ASCII_CELL_PREFIX):
            continue

        if name not in new_names and key not in text_cache:
            continue

        suffix = name[len(ASCII_CELL_PREFIX):]
        try:
            code = int(suffix, 16)
        except ValueError:
            continue

        ascii_cells[chr(code)] = cell

    if not ascii_cells:
        raise RuntimeError(f"No {ASCII_CELL_PREFIX}XX cells found in: {text_gds_path}")

    text_cache[key] = ascii_cells
    return ascii_cells


def validate_ascii_cells_for_text(text: str, ascii_cells: dict[str, pya.Cell]) -> None:
    missing = [ch for ch in text if ch not in ascii_cells]
    if missing:
        raise RuntimeError(f"Missing glyph(s) for XY text: {missing}")


def get_max_glyph_height_um(
    layout: pya.Layout,
    ascii_cells: dict[str, pya.Cell],
    text: str,
) -> float:
    dbu = layout.dbu
    max_height_um = 0.0

    for ch in text:
        glyph = ascii_cells[ch]
        box = glyph.bbox()
        height_um = box.height() * dbu
        if height_um > max_height_um:
            max_height_um = height_um

    if max_height_um <= 0:
        raise RuntimeError(f"Invalid glyph height for text: {text}")

    return max_height_um


def choose_integer_scale_for_text(
    layout: pya.Layout,
    text: str,
    ascii_cells: dict[str, pya.Cell],
    target_bbox_x: float,
    target_bbox_y: float,
    char_space_um: float = XY_CHAR_SPACE_UM,
    allowed_scales: tuple[int, ...] = XY_ALLOWED_SCALES,
) -> int:
    if not text:
        raise RuntimeError("Text is empty")

    base_width_um = get_text_width_um(layout, ascii_cells, text, char_space_um)
    base_height_um = get_max_glyph_height_um(layout, ascii_cells, text)

    valid_scales: list[int] = []

    for scale in allowed_scales:
        width_um = base_width_um * scale
        height_um = base_height_um * scale

        if width_um <= target_bbox_x and height_um <= target_bbox_y:
            valid_scales.append(scale)

    if not valid_scales:
        raise RuntimeError(
            f"Text does not fit bbox: text='{text}', "
            f"bbox=({target_bbox_x}, {target_bbox_y}), "
            f"base=({base_width_um}, {base_height_um})"
        )

    return max(valid_scales)


def create_xy_text_cell_from_gds(
    layout: pya.Layout,
    text: str,
    ascii_cells: dict[str, pya.Cell],
    target_bbox_x: float,
    target_bbox_y: float,
    char_space_um: float = XY_CHAR_SPACE_UM,
    forced_scale: int = 1,
) -> pya.Cell:
    validate_ascii_cells_for_text(text, ascii_cells)

    scale = int(forced_scale)
    if scale <= 0:
        raise RuntimeError(f"Invalid forced_scale: {forced_scale}")

    final_name = f"XY_{text}_{scale}X"
    cell = layout.create_cell(final_name)
    dbu = layout.dbu

    cursor_x_um = 0.0

    for index, ch in enumerate(text):
        glyph = ascii_cells[ch]
        box = glyph.bbox()
        glyph_width_um = box.width() * dbu

        trans = pya.CplxTrans(
            scale,
            0,
            False,
            int(round(cursor_x_um / dbu)),
            0,
        )
        cell.insert(pya.CellInstArray(glyph.cell_index(), trans))

        cursor_x_um += glyph_width_um * scale
        if index != len(text) - 1:
            cursor_x_um += char_space_um * scale

    ensure_bbox_within_limit(
        layout,
        cell,
        target_bbox_x,
        target_bbox_y,
        f"xy_text:{text}",
    )

    return cell


def get_xy_lines(config, row: int, col: int) -> list[str]:
    templates = getattr(config, "xy_lines", None) or [config.xy_format]
    lines: list[str] = []

    for template in templates:
        text = normalize_string(template).format(row=row, col=col)
        if text:
            lines.append(text)

    if not lines:
        raise RuntimeError("No XY text lines generated")

    return lines


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
    manifest: Optional[dict[str, Any]] = None,
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
        paymentSequence=manifest.get("paymentSequence"),
        normalizedRepoName=manifest.get("normalizedRepoName"),
        shortOrderId=manifest.get("shortOrderId"),
        orderId=manifest.get("orderId"),
        sourceRepo=manifest.get("sourceRepo"),
        sourceRunId=manifest.get("sourceRunId"),
        sourceArtifactName=manifest.get("sourceArtifactName"),
    )


# ----------------------------
# User GDS load
# ----------------------------
def read_user_gds_into_layout(layout: pya.Layout, user: UserEntry) -> str:
    top_name = read_gds_into_layout(layout, user.gds)
    expected = normalize_string((user.manifest or {}).get("gdsTopCell"))

    if expected and top_name != expected:
        raise RuntimeError(f"Top mismatch: expected={expected}, got={top_name}")

    return top_name


# ----------------------------
# Wrapper builder
# ----------------------------
def build_user_wrapper_cell(
    layout: pya.Layout,
    user_cell: pya.Cell,
    user_top_name: str,
    config,
    logo_map: dict[str, str],
    row: int,
    col: int,
    tile_index: int,
    user: UserEntry,
    logo_cache: dict[str, pya.Cell],
    ascii_cells: dict[str, pya.Cell],
) -> pya.Cell:
    short_id = normalize_string((user.manifest or {}).get("shortOrderId")) or "unknown"
    wrapper_name = f"WRAP_{user_top_name}_{short_id}"
    wrapper = layout.create_cell(wrapper_name)

    dbu = layout.dbu

    # USER GDS
    insert_instance(wrapper, user_cell, 0.0, 0.0, dbu)

    # LOGO
    tile_number = get_tile_number(user, tile_index)
    for position_number, (x_um, y_um) in enumerate(config.logo_positions, start=1):
        logo_path = resolve_logo_path_for_position(
            config=config,
            logo_map=logo_map,
            tile_number=tile_number,
            position_number=position_number,
        )
        logo_cell = get_or_load_logo_cell(layout, logo_path, logo_cache, config)
        insert_instance(wrapper, logo_cell, x_um, y_um, dbu)

    # Multi-line text block
    lines = get_xy_lines(config, row, col)
    line_pitch = float(getattr(config, "xy_line_pitch", 18.0))

    bbox_x = config.xy_bbox[0]
    bbox_y = config.xy_bbox[1]

    placed_bottom_y_um = 0.0
    line_specs = []

    for line_text in reversed(lines):
        chosen_cell = None
        chosen_scale = None
        chosen_height = None

        for scale in sorted(XY_ALLOWED_SCALES, reverse=True):
            base_width = get_text_width_um(layout, ascii_cells, line_text)
            if base_width * scale > bbox_x:
                continue

            trial_cell = create_xy_text_cell_from_gds(
                layout=layout,
                text=line_text,
                ascii_cells=ascii_cells,
                target_bbox_x=bbox_x,
                target_bbox_y=bbox_y,
                forced_scale=scale,
            )

            box = trial_cell.bbox()
            height_um = box.height() * dbu

            if placed_bottom_y_um + height_um > bbox_y:
                continue

            chosen_cell = trial_cell
            chosen_scale = scale
            chosen_height = height_um
            break

        if chosen_cell is None or chosen_scale is None or chosen_height is None:
            raise RuntimeError(
                f"Line does not fit: '{line_text}', bbox=({bbox_x}, {bbox_y})"
            )

        line_specs.append(
            {
                "cell": chosen_cell,
                "y_um": placed_bottom_y_um,
            }
        )

        placed_bottom_y_um += max(
            line_pitch * chosen_scale,
            chosen_height,
        )

    for spec in line_specs:
        insert_instance(
            wrapper,
            spec["cell"],
            config.xy_pos[0],
            config.xy_pos[1] + spec["y_um"],
            dbu,
        )

    return wrapper


# ----------------------------
# Aggregate
# ----------------------------
def aggregate(config, users, positions, out_gds: Path):
    layout = pya.Layout()
    layout.dbu = 0.001

    top = layout.create_cell(config.top_cell)

    logo_map = load_logo_map(config.logo_map_path)
    logo_cache: dict[str, pya.Cell] = {}
    text_cache: dict[str, dict[str, pya.Cell]] = {}

    ascii_cells = get_or_load_ascii_cells(
        layout=layout,
        text_gds_path=Path(config.xy_text_gds),
        text_cache=text_cache,
    )

    placements: list[Placement] = []
    start_user_index = 0

    # TEG（LOGO/XYなし）
    if config.teg_gds:
        tile_index, row, col, x, y = positions[0]

        top_name = read_gds_into_layout(layout, config.teg_gds)
        cell = layout.cell(top_name)

        if cell is None:
            raise RuntimeError(f"TEG cell not found after read: {config.teg_gds}")

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

    # USERS（LOGO + multi-line text）
    for index, user in enumerate(users):
        tile_index, row, col, x, y = positions[start_user_index + index]

        top_name = read_user_gds_into_layout(layout, user)

        ensure_size_within_pitch(
            layout=layout,
            top_name=top_name,
            pitch_x=config.pitch_x,
            pitch_y=config.pitch_y,
            source=user.gds,
        )

        user_cell = layout.cell(top_name)
        if user_cell is None:
            raise RuntimeError(f"User cell not found after read: {user.gds}")

        wrapper = build_user_wrapper_cell(
            layout=layout,
            user_cell=user_cell,
            user_top_name=top_name,
            config=config,
            logo_map=logo_map,
            row=row,
            col=col,
            tile_index=tile_index,
            user=user,
            logo_cache=logo_cache,
            ascii_cells=ascii_cells,
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

    # FILL（LOGO/XYなし）
    fill_start = start_user_index + len(users)
    remain = len(positions) - fill_start

    if remain > 0:
        if not config.fill_gds:
            raise RuntimeError("fill_gds is required for remaining empty tiles")

        fill_top = read_gds_into_layout(layout, config.fill_gds)
        fill_cell = layout.cell(fill_top)

        if fill_cell is None:
            raise RuntimeError(f"Fill cell not found after read: {config.fill_gds}")

        for offset in range(remain):
            tile_index, row, col, x, y = positions[fill_start + offset]
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