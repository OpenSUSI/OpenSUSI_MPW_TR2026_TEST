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


def normalize_name(value: str) -> str:
    s = str(value or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def extract_repo_name(source_repo: str) -> str:
    value = str(source_repo or "").strip()
    parts = value.split("/")
    if len(parts) >= 2 and parts[-1]:
        return parts[-1]
    return value or "unknown"


def make_short_order_id(order_id: str) -> str:
    return str(order_id).replace("-", "")[:10]


def build_top_cell_name(github_id: str, repo_name: str) -> str:
    gid = normalize_name(github_id)
    repo = normalize_name(repo_name)
    return f"tr_1um_{gid}_{repo}"[:64]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--github-id", required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-artifact-name", required=True)

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    repo_name = extract_repo_name(args.source_repo)
    normalized_repo_name = normalize_name(repo_name)
    short_order_id = make_short_order_id(args.order_id)
    gds_top_cell = build_top_cell_name(args.github_id, repo_name)

    manifest = {
        "orderId": args.order_id,
        "shortOrderId": short_order_id,
        "githubId": args.github_id,
        "sourceRepo": args.source_repo,
        "normalizedRepoName": normalized_repo_name,
        "gdsTopCell": gds_top_cell,
        "sourceRunId": args.source_run_id,
        "sourceArtifactName": args.source_artifact_name,
    }

    (target_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()