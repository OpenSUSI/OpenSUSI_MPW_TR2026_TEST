# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import re


SYSTEM_DIRS = {"000_system"}
USER_GDS_FILENAME = "GDSII_MDP.gds"
USER_MANIFEST_FILENAME = "manifest.json"


@dataclass
class UserEntry:
    github_id: str
    repo_name: str
    normalized_repo_name: str
    payment_sequence: int
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


def order_id_to_dir_name(order_id: Any) -> str:
    """Convert ORD-YYYYMMDD-XXXXXX to ORD-YYMMDD-XXXXXX for directory names."""
    value = normalize_string(order_id)
    match = re.fullmatch(r"ORD-20([0-9]{2})([0-9]{2})([0-9]{2})-(.+)", value)

    if not match:
        return value

    yy, mm, dd, suffix = match.groups()
    return f"ORD-{yy}{mm}{dd}-{suffix}"


def validate_manifest(manifest: dict[str, Any], path: Path) -> None:
    required = [
        "orderId",
        "paymentSequence",
        "githubId",
        "sourceRepo",
        "normalizedRepoName",
        "gdsTopCell",
    ]

    missing = [key for key in required if manifest.get(key) in (None, "", [])]

    if missing:
        raise RuntimeError(f"Invalid manifest: missing {missing}, path={path}")

    payment_sequence = normalize_int(manifest.get("paymentSequence"))
    if payment_sequence <= 0:
        raise RuntimeError(
            f"Invalid manifest: paymentSequence must be > 0, path={path}"
        )


def validate_slot_dir(slot_dir: Path, manifest: dict[str, Any]) -> None:
    """Validate users/<githubId>/<orderDir>/<slot>/ consistency.

    orderDir is derived from orderId.
    Example:
      orderId  = ORD-20260504-003216
      orderDir = ORD-260504-003216
    """
    payment_sequence = normalize_int(manifest.get("paymentSequence"))
    expected_slot = f"{payment_sequence:02d}"

    if slot_dir.name != expected_slot:
        raise RuntimeError(
            "Invalid submission path: "
            f"slot dir '{slot_dir.name}' does not match "
            f"paymentSequence '{expected_slot}', path={slot_dir}"
        )

    expected_order_dir = order_id_to_dir_name(manifest.get("orderId"))
    if expected_order_dir and slot_dir.parent.name != expected_order_dir:
        raise RuntimeError(
            "Invalid submission path: "
            f"order dir '{slot_dir.parent.name}' does not match "
            f"orderId-derived dir '{expected_order_dir}', path={slot_dir}"
        )

    github_id = normalize_string(manifest.get("githubId"))
    if github_id and slot_dir.parent.parent.name != github_id:
        raise RuntimeError(
            "Invalid submission path: "
            f"github dir '{slot_dir.parent.parent.name}' does not match "
            f"githubId '{github_id}', path={slot_dir}"
        )


def collect_users(users_dir: Path) -> list[UserEntry]:
    """
    Collect user submissions from the slot-aware layout only.

    Expected layout:
      users/<githubId>/<orderDir>/<slot>/GDSII_MDP.gds
      users/<githubId>/<orderDir>/<slot>/manifest.json

    orderDir is derived from orderId:
      ORD-YYYYMMDD-XXXXXX -> ORD-YYMMDD-XXXXXX
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

            for slot_dir in sorted(order_dir.iterdir(), key=lambda path: path.name):
                if not slot_dir.is_dir():
                    continue

                gds = slot_dir / USER_GDS_FILENAME
                manifest_path = slot_dir / USER_MANIFEST_FILENAME

                if not gds.exists():
                    raise FileNotFoundError(f"GDS not found: {gds}")

                if not manifest_path.exists():
                    raise FileNotFoundError(
                        f"manifest.json not found: {manifest_path}"
                    )

                manifest = load_json(manifest_path)
                validate_manifest(manifest, manifest_path)
                validate_slot_dir(slot_dir, manifest)

                github_id = normalize_string(manifest.get("githubId"))
                source_repo = normalize_string(manifest.get("sourceRepo"))
                repo_name = extract_repo_name(source_repo)
                normalized_repo_name = (
                    normalize_string(manifest.get("normalizedRepoName")) or repo_name
                )
                payment_sequence = normalize_int(manifest.get("paymentSequence"))

                users.append(
                    UserEntry(
                        github_id=github_id,
                        repo_name=repo_name,
                        normalized_repo_name=normalized_repo_name,
                        payment_sequence=payment_sequence,
                        gds=gds,
                        manifest_path=manifest_path,
                        manifest=manifest,
                    )
                )

    return users
