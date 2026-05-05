#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ -----

import argparse
import json
import re
from pathlib import Path


MAX_GDS_CELL_NAME_LEN = 64


def normalize_name(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def extract_repo_name(source_repo: str) -> str:
    value = str(source_repo or "").strip()
    parts = value.split("/")

    if len(parts) >= 2 and parts[-1]:
        return parts[-1]

    return value or "unknown"


def order_id_to_short_id(order_id: str) -> str:
    safe = str(order_id or "").strip()

    match = re.match(r"^ORD-20(\d{2})(\d{2})(\d{2})-(.+)$", safe)
    if match:
        return f"ORD-{match.group(1)}{match.group(2)}{match.group(3)}-{match.group(4)}"

    return safe


def build_top_cell_name(
    github_id: str,
    repo_name: str,
    order_id: str,
    slot_id: str
) -> str:
    normalized_github_id = normalize_name(github_id)
    normalized_repo_name = normalize_name(repo_name)
    normalized_order_id = normalize_name(order_id_to_short_id(order_id))
    normalized_slot_id = normalize_name(slot_id)

    return (
        f"tr_1um_{normalized_github_id}_"
        f"{normalized_repo_name}_"
        f"{normalized_order_id}_"
        f"{normalized_slot_id}"
    )[:MAX_GDS_CELL_NAME_LEN]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write import manifest.json for an imported submission."
    )

    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--github-id", required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-artifact-name", required=True)
    parser.add_argument("--payment-sequence", required=True, type=int)
    parser.add_argument("--slot-id", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    repo_name = extract_repo_name(args.source_repo)
    normalized_repo_name = normalize_name(repo_name)

    gds_top_cell = build_top_cell_name(
        args.github_id,
        repo_name,
        args.order_id,
        args.slot_id,
    )

    manifest = {
        "orderId": str(args.order_id),
        "paymentSequence": int(args.payment_sequence),
        "slotId": str(args.slot_id),
        "githubId": str(args.github_id),
        "sourceRepo": str(args.source_repo),
        "normalizedRepoName": normalized_repo_name,
        "gdsTopCell": gds_top_cell,
        "sourceRunId": str(args.source_run_id),
        "sourceArtifactName": str(args.source_artifact_name),
    }

    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()