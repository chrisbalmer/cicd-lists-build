#!/usr/bin/env python3
"""Validate XSOAR/XSIAM list files based on their type defined in metadata."""

import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import yaml


def load_metadata(metadata_path: Path) -> dict:
    """Load and return the metadata YAML for a list."""
    with open(metadata_path) as f:
        return yaml.safe_load(f)


def find_data_file(list_dir: Path, metadata: dict) -> Path:
    """Find the raw data file paired with the metadata file."""
    # The data file should be any non-metadata file in the directory
    for f in list_dir.iterdir():
        if f.name != "metadata.yml" and f.is_file():
            return f
    raise FileNotFoundError(f"No data file found in {list_dir}")


def validate_json(data_path: Path) -> bool:
    """Validate that the file contains valid JSON."""
    try:
        with open(data_path) as f:
            json.load(f)
        print(f"  PASS: {data_path} is valid JSON")
        return True
    except json.JSONDecodeError as e:
        print(f"  FAIL: {data_path} is not valid JSON: {e}")
        return False


def validate_csv(data_path: Path) -> bool:
    """Validate that the file contains valid CSV."""
    try:
        with open(data_path, newline="") as f:
            content = f.read()
        # Attempt to sniff the dialect and parse
        reader = csv.reader(io.StringIO(content))
        row_count = 0
        col_count = None
        for row in reader:
            row_count += 1
            if col_count is None:
                col_count = len(row)
            elif len(row) != col_count:
                print(
                    f"  FAIL: {data_path} has inconsistent column count "
                    f"(row {row_count}: expected {col_count}, got {len(row)})"
                )
                return False
        if row_count == 0:
            print(f"  FAIL: {data_path} is empty")
            return False
        print(f"  PASS: {data_path} is valid CSV ({row_count} rows, {col_count} columns)")
        return True
    except csv.Error as e:
        print(f"  FAIL: {data_path} is not valid CSV: {e}")
        return False


def validate_custom(data_path: Path, list_dir: Path) -> bool:
    """Run a custom Python validation script for the list."""
    custom_script = Path(__file__).parent / "custom_validators" / f"{list_dir.name}.py"
    if not custom_script.exists():
        # Fall back to the default custom validator
        custom_script = Path(__file__).parent / "custom_validators" / "default.py"
    if not custom_script.exists():
        print(f"  FAIL: No custom validator found for {list_dir.name}")
        return False
    result = subprocess.run(
        [sys.executable, str(custom_script), str(data_path)],
        capture_output=True,
        text=True,
    )
    if result.stdout:
        for line in result.stdout.strip().splitlines():
            print(f"  {line}")
    if result.returncode != 0:
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"  ERROR: {line}")
        print(f"  FAIL: Custom validation failed for {data_path}")
        return False
    print(f"  PASS: Custom validation passed for {data_path}")
    return True


VALIDATORS = {
    "json": validate_json,
    "csv": validate_csv,
}


def validate_list(list_dir: Path) -> bool:
    """Validate a single list directory."""
    metadata_path = list_dir / "metadata.yml"
    if not metadata_path.exists():
        print(f"SKIP: {list_dir} has no metadata.yml")
        return True

    metadata = load_metadata(metadata_path)

    # Validate required metadata fields
    required_fields = ["id", "name", "type"]
    missing = [f for f in required_fields if f not in metadata]
    if missing:
        print(f"FAIL: {metadata_path} is missing required fields: {', '.join(missing)}")
        return False

    list_type = metadata["type"].lower()
    list_name = metadata["name"]

    print(f"Validating list: {list_name} (type: {list_type})")

    try:
        data_path = find_data_file(list_dir, metadata)
    except FileNotFoundError as e:
        print(f"  FAIL: {e}")
        return False

    if list_type == "custom":
        return validate_custom(data_path, list_dir)
    elif list_type in VALIDATORS:
        return VALIDATORS[list_type](data_path)
    else:
        print(f"  FAIL: Unknown list type '{list_type}' in {metadata_path}")
        return False


def get_changed_lists(target_dirs: list[Path] | None = None) -> list[Path]:
    """Get list directories to validate. If target_dirs is provided, use those.
    Otherwise, discover all list directories under Lists/."""
    if target_dirs:
        return target_dirs
    lists_root = Path("Lists")
    if not lists_root.exists():
        return []
    return [d for d in lists_root.iterdir() if d.is_dir() and (d / "metadata.yml").exists()]


def main():
    # Accept specific list directories as arguments, or validate all
    if len(sys.argv) > 1:
        target_dirs = [Path(p) for p in sys.argv[1:]]
    else:
        target_dirs = None

    list_dirs = get_changed_lists(target_dirs)

    if not list_dirs:
        print("No lists found to validate.")
        sys.exit(0)

    all_passed = True
    for list_dir in sorted(list_dirs):
        if not validate_list(list_dir):
            all_passed = False

    if all_passed:
        print("\nAll validations passed!")
        sys.exit(0)
    else:
        print("\nSome validations failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
