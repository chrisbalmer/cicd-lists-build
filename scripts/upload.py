#!/usr/bin/env python3
"""Upload changed XSOAR/XSIAM lists using demisto-sdk.

Detects which list directories changed in the last merge commit and uploads
them via demisto-sdk. Lists live under Packs/<PackName>/Lists/<ListName>/.

Requires the following environment variables:
  DEMISTO_BASE_URL  - The XSOAR/XSIAM server URL
  DEMISTO_API_KEY   - The API key for authentication
  XSIAM_AUTH_ID     - The auth ID (for XSIAM)
"""

import os
import subprocess
import sys
from pathlib import Path


def get_changed_lists() -> list[Path]:
    """Get list directories that changed in the last merge commit."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1", "HEAD", "--", "Packs/"],
        capture_output=True,
        text=True,
        check=True,
    )
    changed_files = result.stdout.strip().splitlines()
    list_dirs = set()
    for f in changed_files:
        parts = Path(f).parts
        # Match Packs/<Pack>/Lists/<ListName>/...
        if len(parts) >= 4 and parts[0] == "Packs" and parts[2] == "Lists":
            list_dirs.add(Path(*parts[:4]))
    return sorted(list_dirs)


def upload_list(list_dir: Path) -> bool:
    """Upload a single list using demisto-sdk."""
    print(f"Uploading list: {list_dir}")
    result = subprocess.run(
        ["demisto-sdk", "upload", "-i", str(list_dir)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"Failed to upload {list_dir}", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return False
    return True


def main():
    required_vars = ["DEMISTO_BASE_URL", "DEMISTO_API_KEY", "XSIAM_AUTH_ID"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    changed = get_changed_lists()
    if not changed:
        print("No lists changed in this commit.")
        sys.exit(0)

    print(f"Found {len(changed)} changed list(s):")
    for d in changed:
        print(f"  - {d}")

    all_ok = True
    for list_dir in changed:
        if not upload_list(list_dir):
            all_ok = False

    if not all_ok:
        print("\nSome uploads failed!", file=sys.stderr)
        sys.exit(1)
    print("\nAll uploads completed successfully!")


if __name__ == "__main__":
    main()
