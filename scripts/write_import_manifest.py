#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", required=True)
    parser.add_argument("--order-id", required=True)
    parser.add_argument("--github-id", required=True)
    parser.add_argument("--source-repo", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-artifact-name", required=True)
    args = parser.parse_args()

    target_dir = Path(args.target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "orderId": args.order_id,
        "githubId": args.github_id,
        "sourceRepo": args.source_repo,
        "sourceRunId": args.source_run_id,
        "sourceArtifactName": args.source_artifact_name,
    }

    (target_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2)
    )


if __name__ == "__main__":
    main()