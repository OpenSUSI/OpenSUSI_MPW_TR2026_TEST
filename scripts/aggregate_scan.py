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

    # New placement identity:
    # submission_sequence == manifest["submissionSequence"]    # Compatibility name:
    submission_sequence: int

    gds: Path
    manifest_path: Path
    manifest: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def normalize_string(value: Any) -> str:
    return str(value or "").strip()


def normalize_int(value: Any) -> int:
    text = normalize_string(value)

    if not text:
        return 0

    try:
        return int(text)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer value: {value}") from exc


def extract_repo_name(source_repo: str) -> str:
    value = normalize_string(source_repo)
    parts = value.split("/")

    if len(parts) >= 2 and parts[-1]:
        return parts[-1]

    return value or "unknown"


def validate_manifest(manifest: dict[str, Any], path: Path) -> None:
    required = [
        "orderId",
        "submissionSequence",
        "githubId",
        "sourceRepo",
        "normalizedRepoName",
        "gdsTopCell",
    ]

    missing = [
        key for key in required
        if manifest.get(key) in (None, "", [])
    ]

    if missing:
        raise RuntimeError(f"Invalid manifest: missing {missing}, path={path}")

    submission_sequence = normalize_int(manifest.get("submissionSequence"))

    if submission_sequence <= 0:
        raise RuntimeError(
            f"Invalid manifest: submissionSequence must be > 0, path={path}"
        )


def validate_order_dir(order_dir: Path, manifest: dict[str, Any]) -> None:
    """
    New MPW layout:

      users/<githubId>/<orderId>/GDSII_MDP.gds
      users/<githubId>/<orderId>/manifest.json

    No slotId / slotNo directory exists anymore.
    """
    order_id = normalize_string(manifest.get("orderId"))

    if order_id and order_dir.name != order_id:
        raise RuntimeError(
            "Invalid submission path: "
            f"order dir '{order_dir.name}' does not match "
            f"orderId '{order_id}', path={order_dir}"
        )

    github_id = normalize_string(manifest.get("githubId"))

    if github_id and order_dir.parent.name != github_id:
        raise RuntimeError(
            "Invalid submission path: "
            f"github dir '{order_dir.parent.name}' does not match "
            f"githubId '{github_id}', path={order_dir}"
        )


def collect_users(users_dir: Path) -> list[UserEntry]:
    """
    Collect user submissions from the order-based layout.

    Expected layout:
      users/<githubId>/<orderId>/GDSII_MDP.gds
      users/<githubId>/<orderId>/manifest.json

    New model:
      orderId = storage identity
      submissionSequence = placement identity
    """
    if not users_dir.exists():
        raise FileNotFoundError(f"users dir not found: {users_dir}")

    users: list[UserEntry] = []

    for github_dir in sorted(users_dir.iterdir(), key=lambda path: path.name):
        if not github_dir.is_dir() or github_dir.name in SYSTEM_DIRS:
            continue

        for order_dir in sorted(github_dir.iterdir(), key=lambda path: path.name):
            if not order_dir.is_dir():
                continue

            gds = order_dir / USER_GDS_FILENAME
            manifest_path = order_dir / USER_MANIFEST_FILENAME

            if not gds.exists():
                raise FileNotFoundError(f"GDS not found: {gds}")

            if not manifest_path.exists():
                raise FileNotFoundError(
                    f"manifest.json not found: {manifest_path}"
                )

            manifest = load_json(manifest_path)
            validate_manifest(manifest, manifest_path)
            validate_order_dir(order_dir, manifest)

            github_id = normalize_string(manifest.get("githubId"))
            source_repo = normalize_string(manifest.get("sourceRepo"))
            repo_name = extract_repo_name(source_repo)
            normalized_repo_name = (
                normalize_string(manifest.get("normalizedRepoName")) or repo_name
            )
            submission_sequence = normalize_int(
                manifest.get("submissionSequence")
            )

            users.append(
                UserEntry(
                    github_id=github_id,
                    repo_name=repo_name,
                    normalized_repo_name=normalized_repo_name,

                    # Compatibility field name.
                    submission_sequence=submission_sequence,
                    gds=gds,
                    manifest_path=manifest_path,
                    manifest=manifest,
                )
            )

    return users