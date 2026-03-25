# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re


SYSTEM_DIRS = {"00_system", "000_system"}
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


def normalize_repo_name(value: Any) -> str:
    s = normalize_string(value).lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def extract_repo_name(source_repo: str) -> str:
    value = normalize_string(source_repo)
    if not value:
        return ""

    parts = value.split("/")
    if len(parts) >= 2 and parts[-1]:
        return parts[-1]

    return value


def collect_users(users_dir: Path) -> list[UserEntry]:
    if not users_dir.exists():
        raise FileNotFoundError(f"users dir not found: {users_dir}")

    users: list[UserEntry] = []

    # users/<githubId>/<normalizedRepoName>/
    for github_dir in sorted(users_dir.iterdir(), key=lambda p: p.name):
        if not github_dir.is_dir():
            continue

        if github_dir.name in SYSTEM_DIRS:
            continue

        for repo_dir in sorted(github_dir.iterdir(), key=lambda p: p.name):
            if not repo_dir.is_dir():
                continue

            gds = repo_dir / USER_GDS_FILENAME
            manifest_path = repo_dir / USER_MANIFEST_FILENAME

            if not gds.exists():
                raise FileNotFoundError(f"GDS not found: {gds}")

            if not manifest_path.exists():
                raise FileNotFoundError(f"manifest.json not found: {manifest_path}")

            manifest = load_json(manifest_path)

            github_id = normalize_string(manifest.get("githubId")) or github_dir.name
            source_repo = normalize_string(manifest.get("sourceRepo"))
            repo_name = extract_repo_name(source_repo) or repo_dir.name
            normalized_repo_name = (
                normalize_string(manifest.get("normalizedRepoName"))
                or normalize_repo_name(repo_name)
                or repo_dir.name
            )

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