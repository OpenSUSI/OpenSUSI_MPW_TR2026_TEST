# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
def build_positions(grid_x: int, grid_y: int, pitch_x: float, pitch_y: float):
    """
    Build tile-center positions so that:
    - tile coordinate (0,0) is the upper-left slot
    - slots advance left-to-right within a row
    - then top-to-bottom by rows
    - the overall tiled BBOX center is always at (0,0)

    Returns:
      [(tile_index, row, col, x, y), ...]
    """

    positions = []
    tile_index = 0

    x0 = (grid_x - 1) / 2.0
    y0 = (grid_y - 1) / 2.0

    for row in range(grid_y):
        for col in range(grid_x):
            x = (col - x0) * pitch_x
            y = (y0 - row) * pitch_y
            positions.append((tile_index, row, col, x, y))
            tile_index += 1

    return positions