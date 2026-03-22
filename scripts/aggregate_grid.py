# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
def build_positions(grid_x: int, grid_y: int, pitch_x: float, pitch_y: float):
    """
    Build tile-center positions so that the total tiled BBOX center is always (0, 0).

    Placement order:
    - start from upper-right
    - move right to left
    - then next row downward

    Returns:
      [(tile_index, row, col, x, y), ...]
    """

    x_centers = [((grid_x - 1) / 2.0 - i) * pitch_x for i in range(grid_x)]
    y_centers = [((grid_y - 1) / 2.0 - i) * pitch_y for i in range(grid_y)]

    positions = []
    tile_index = 0

    for row, y in enumerate(y_centers):
        for col, x in enumerate(x_centers):
            positions.append((tile_index, row, col, x, y))
            tile_index += 1

    return positions