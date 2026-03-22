# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json


@dataclass
class Placement:
    type: str
    githubId: str
    gdsFile: str
    gdsTopCell: str
    x: float
    y: float
    tileIndex: int
    row: Optional[int]
    col: Optional[int]
    orderId: Optional[str] = None
    sourceRepo: Optional[str] = None
    sourceRunId: Optional[str] = None
    sourceArtifactName: Optional[str] = None


def write_manifest(path: Path, config, placements: list[Placement], output_gds: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "topCell": config.top_cell,
        "outputGds": str(output_gds).replace("\\", "/"),
        "pitch": {
            "x": config.pitch_x,
            "y": config.pitch_y,
        },
        "grid": {
            "x": config.grid_x,
            "y": config.grid_y,
        },
        "entries": [asdict(p) for p in placements],
    }

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )