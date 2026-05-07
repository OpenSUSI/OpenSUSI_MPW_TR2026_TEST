#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_ARTIFACT_NAME = "GDSII_MDP"
DEFAULT_GDS_FILENAME = "GDSII_MDP.gds"
DEFAULT_MANIFEST_FILENAME = "manifest.json"


def normalize_string(value: object) -> str:
    return str(value or "").strip()


def normalize_repo_name(value: str) -> str:
    raw = normalize_string(value)
    raw = re.sub(r"^https?://github\.com/", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"^github\.com/", "", raw, flags=re.IGNORECASE)
    return raw.strip("/")


def sanitize_identifier(value: str) -> str:
    raw = normalize_string(value)
    raw = re.sub(r"[^A-Za-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw)
    raw = raw.strip("_")
    return raw or "unknown"


def build_top_cell_name(order_id: str) -> str:
    """
    New MPW model:
      one orderId = one GDSII submission

    Top cell name is derived only from orderId.

    Example:
      ORD-260507-104500-01
        -> ORD_260507_104500_01
    """
    return sanitize_identifier(order_id)


def build_manifest(args: argparse.Namespace) -> dict:
    normalized_repo = normalize_repo_name(args.source_repo)

    gds_top_cell = normalize_string(args.gds_top_cell) or build_top_cell_name(
      args.order_id
    )

    return {
        "orderId": normalize_string(args.order_id),
        "submissionSequence": int(args.submission_sequence),
        "githubId": normalize_string(args.github_id),
        "sourceRepo": normalized_repo,
        "sourceRunId": normalize_string(args.source_run_id),
        "sourceArtifactName": normalize_string(args.source_artifact_name),
        "normalizedRepoName": normalized_repo,
        "gdsFile": normalize_string(args.gds_file),
        "gdsTopCell": gds_top_cell,
    }


def validate_manifest(manifest: dict) -> None:
    required = [
        "orderId",
        "submissionSequence",
        "githubId",
        "sourceRepo",
        "sourceRunId",
        "sourceArtifactName",
        "normalizedRepoName",
        "gdsFile",
        "gdsTopCell",
    ]

    missing = [
        key for key in required
        if manifest.get(key) in (None, "")
    ]

    if missing:
        raise ValueError(
            f"Missing required manifest fields: {', '.join(missing)}"
        )

    submission_sequence = int(manifest["submissionSequence"])

    if submission_sequence <= 0:
        raise ValueError(
            f"submissionSequence must be positive: {submission_sequence}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write MPW import manifest for one order-based submission."
    )

    parser.add_argument(
        "--order-id",
        required=True,
        help="Full MPW order ID. Example: ORD-260507-104500-01",
    )

    parser.add_argument(
        "--submission-sequence",
        required=True,
        type=int,
        help="Global deterministic placement sequence.",
    )

    parser.add_argument(
        "--github-id",
        required=True,
        help="GitHub owner/user ID.",
    )

    parser.add_argument(
        "--source-repo",
        required=True,
        help="Source GitHub repository, owner/repo or GitHub URL.",
    )

    parser.add_argument(
        "--source-run-id",
        required=True,
        help="Source GitHub Actions run ID.",
    )

    parser.add_argument(
        "--source-artifact-name",
        default=DEFAULT_ARTIFACT_NAME,
        help="Source artifact name. Default: GDSII_MDP",
    )

    parser.add_argument(
        "--gds-file",
        default=DEFAULT_GDS_FILENAME,
        help="Imported GDS file name. Default: GDSII_MDP.gds",
    )

    parser.add_argument(
        "--gds-top-cell",
        default="",
        help="Optional override for GDS top cell name.",
    )

    parser.add_argument(
        "--output",
        default=DEFAULT_MANIFEST_FILENAME,
        help="Output manifest path. Default: manifest.json",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    manifest = build_manifest(args)
    validate_manifest(manifest)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote manifest: {output_path}")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())