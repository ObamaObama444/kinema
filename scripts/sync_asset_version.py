#!/usr/bin/env python3
"""Sync the shared frontend asset version into static HTML entrypoints."""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VERSION_FILE = REPO_ROOT / "frontend" / ".asset-version"
DEFAULT_GLOBS = (
    "frontend/**/*.html",
)
VERSION_PATTERN = re.compile(r"(\?v=)([^\"'\s>]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version-file",
        type=Path,
        default=DEFAULT_VERSION_FILE,
        help="Path to the shared asset version file.",
    )
    parser.add_argument(
        "--version",
        help="Explicit asset version to apply.",
    )
    parser.add_argument(
        "--bump",
        action="store_true",
        help="Generate a fresh version token before syncing.",
    )
    return parser.parse_args()


def resolve_version(args: argparse.Namespace) -> str:
    if args.version:
        version = args.version.strip()
    elif args.bump:
        version = "miniapp_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    else:
        version = args.version_file.read_text(encoding="utf-8").strip()

    if not version:
        raise SystemExit("Asset version is empty.")

    args.version_file.write_text(version + "\n", encoding="utf-8")
    return version


def sync_file(path: Path, version: str) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = VERSION_PATTERN.sub(r"\1" + version, original)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    args = parse_args()
    version = resolve_version(args)
    updated_paths: list[Path] = []

    for pattern in DEFAULT_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if sync_file(path, version):
                updated_paths.append(path)

    print(f"Synced asset version {version} into {len(updated_paths)} static HTML file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
