# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


SYSTEM_DIRS = {"000_system"}
USER_GDS_FILENAME = "GDSII_MDP.gds"
USER_MANIFEST_FILENAME = "manifest.json"


@dataclass
class UserEntry:
    github_id: str
    repo_name: str
    normalized_repo_name: str
    gds: Path
    manifest_path: Path
    manifest: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_string(value: Any) -> str:
    return str(value or "").strip()


def extract_repo_name(source_repo: str) -> str:
    value = normalize_string(source_repo)
    parts = value.split("/")

    if len(parts) >= 2 and parts[-1]:
        return parts[-1]

    return value or "unknown"


def validate_manifest(manifest: dict, path: Path) -> None:
    required = [
        "orderId",
        "shortOrderId",
        "githubId",
        "sourceRepo",
        "normalizedRepoName",
        "gdsTopCell",
    ]

    missing = [k for k in required if not manifest.get(k)]

    if missing:
        raise RuntimeError(
            f"Invalid manifest: missing {missing}, path={path}"
        )


def collect_users(users_dir: Path) -> list[UserEntry]:
    if not users_dir.exists():
        raise FileNotFoundError(f"users dir not found: {users_dir}")

    users: list[UserEntry] = []

    # users/<githubId>/<shortOrderId>/
    for github_dir in sorted(users_dir.iterdir(), key=lambda p: p.name):
        if not github_dir.is_dir() or github_dir.name in SYSTEM_DIRS:
            continue

        for order_dir in sorted(github_dir.iterdir(), key=lambda p: p.name):
            if not order_dir.is_dir():
                continue

            gds = order_dir / USER_GDS_FILENAME
            manifest_path = order_dir / USER_MANIFEST_FILENAME

            if not gds.exists():
                raise FileNotFoundError(f"GDS not found: {gds}")

            if not manifest_path.exists():
                raise FileNotFoundError(f"manifest.json not found: {manifest_path}")

            manifest = load_json(manifest_path)
            validate_manifest(manifest, manifest_path)

            github_id = normalize_string(manifest.get("githubId")) or github_dir.name
            source_repo = normalize_string(manifest.get("sourceRepo"))

            repo_name = extract_repo_name(source_repo)
            normalized_repo_name = normalize_string(
                manifest.get("normalizedRepoName")
            ) or repo_name

            users.append(
                UserEntry(
                    github_id=github_id,
                    repo_name=repo_name,
                    normalized_repo_name=normalized_repo_name,
                    gds=gds,
                    manifest_path=manifest_path,
                    manifest=manifest,
                )
            )

    return users