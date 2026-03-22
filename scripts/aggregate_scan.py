# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


SYSTEM_DIRS = {"00_system", "000_system"}
USER_GDS_FILENAME = "GDSII_MDP.gds"
USER_MANIFEST_FILENAME = "manifest.json"


@dataclass
class UserEntry:
    github_id: str
    gds: Path
    manifest_path: Path
    manifest: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def collect_users(users_dir: Path) -> list[UserEntry]:
    if not users_dir.exists():
        raise FileNotFoundError(f"users dir not found: {users_dir}")

    users: list[UserEntry] = []

    for directory in sorted(users_dir.iterdir(), key=lambda p: p.name):
        if not directory.is_dir():
            continue

        if directory.name in SYSTEM_DIRS:
            continue

        gds = directory / USER_GDS_FILENAME
        manifest_path = directory / USER_MANIFEST_FILENAME

        if not gds.exists():
            raise FileNotFoundError(f"GDS not found: {gds}")

        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found: {manifest_path}")

        users.append(
            UserEntry(
                github_id=directory.name,
                gds=gds,
                manifest_path=manifest_path,
                manifest=load_json(manifest_path),
            )
        )

    return users