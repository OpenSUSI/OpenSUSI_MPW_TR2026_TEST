#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ -----
# OpenSUSI jun1okamura <jun1okamura@gmail.com>
# LICENSE: Apache License Version 2.0
# ----- ------ ----- ----- ------ ----- ----- ------ -----

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_artifact_id(data: dict, name: str) -> int:
    for artifact in data.get("artifacts", []):
        if artifact.get("name") == name:
            return artifact.get("id")

    raise RuntimeError(f"Artifact not found: {name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve artifact ID from GitHub API response")
    parser.add_argument("--json-file", required=True, type=Path)
    parser.add_argument("--artifact-name", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        data = load_json(args.json_file)
        artifact_id = find_artifact_id(data, args.artifact_name)
        print(artifact_id)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()