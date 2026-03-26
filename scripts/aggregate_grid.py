# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from typing import List, Tuple


def build_positions(
    grid_x: int,
    grid_y: int,
    pitch_x: float,
    pitch_y: float,
) -> List[Tuple[int, int, int, float, float]]:
    """
    Generate tile center positions.

    - (0,0) is top-left
    - left → right, then top → bottom
    - layout center is always (0,0)

    Returns:
        [(tile_index, row, col, x, y), ...]
    """

    positions: List[Tuple[int, int, int, float, float]] = []

    x0 = (grid_x - 1) / 2.0
    y0 = (grid_y - 1) / 2.0

    for tile_index, (row, col) in enumerate(
        (r, c) for r in range(grid_y) for c in range(grid_x)
    ):
        x = (col - x0) * pitch_x
        y = (y0 - row) * pitch_y
        positions.append((tile_index, row, col, x, y))

    return positions