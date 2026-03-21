#!/usr/bin/env python3
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 
# OpenSUSI jun1okamura <jun1okamura@gmail.com>  
# LICENSE: Apache License Version 2.0, January 2004,
#          http://www.apache.org/licenses/
# ----- ------ ----- ----- ------ ----- ----- ------ ----- 

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-file", required=True)
    parser.add_argument("--artifact-name", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.json_file).read_text())

    for a in data.get("artifacts", []):
        if a.get("name") == args.artifact_name:
            print(a["id"])
            return

    print("Artifact not found", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
