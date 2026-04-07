#!/usr/bin/env python3
"""Start a localhost.run tunnel and write the discovered public URL into .codex-runtime."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUNTIME_DIR = REPO_ROOT / ".codex-runtime"
DEFAULT_URL_FILE = DEFAULT_RUNTIME_DIR / "backend-tunnel-url.txt"
DEFAULT_LOG_FILE = DEFAULT_RUNTIME_DIR / "backend-tunnel.log"
URL_PATTERN = re.compile(r"https://[A-Za-z0-9.-]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open a localhost.run tunnel for the local backend and persist the public URL."
    )
    parser.add_argument("--port", type=int, default=8000, help="Local backend port to expose.")
    parser.add_argument(
        "--url-file",
        type=Path,
        default=DEFAULT_URL_FILE,
        help="Where to write the discovered public tunnel URL.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help="Where to mirror tunnel stdout/stderr.",
    )
    return parser.parse_args()


def extract_url(line: str) -> str | None:
    if "tunneled with tls termination" not in line:
        return None
    match = URL_PATTERN.search(line)
    return match.group(0) if match else None


def main() -> int:
    args = parse_args()
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    args.url_file.parent.mkdir(parents=True, exist_ok=True)
    args.url_file.write_text("", encoding="utf-8")
    args.log_file.write_text("", encoding="utf-8")

    command = [
        "ssh",
        "-T",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ExitOnForwardFailure=yes",
        "-R",
        f"80:127.0.0.1:{args.port}",
        "nokey@localhost.run",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )

    discovered_url: str | None = None
    try:
        assert process.stdout is not None
        with args.log_file.open("a", encoding="utf-8") as log_file:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                log_file.write(line)
                log_file.flush()

                next_url = extract_url(line)
                if next_url and next_url != discovered_url:
                    discovered_url = next_url
                    args.url_file.write_text(discovered_url + "\n", encoding="utf-8")
                    print(f"[tunnel-url] {discovered_url}", flush=True)
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
