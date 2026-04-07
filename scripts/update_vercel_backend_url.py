#!/usr/bin/env python3
"""Update frontend/vercel.json rewrites to point at the current backend tunnel."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "frontend" / "vercel.json"
DEFAULT_NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
DEFAULT_RUNTIME_URL_FILE = REPO_ROOT / ".codex-runtime" / "backend-tunnel-url.txt"
REWRITE_SUFFIXES = {
    "/health": "/health",
    "/api/:path*": "/api/:path*",
    "/static/:path*": "/static/:path*",
    "/login": "/login",
    "/register": "/register",
    "/app": "/app",
    "/app/:path*": "/app/:path*",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Vercel rewrites with the current backend tunnel URL."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to vercel.json (default: frontend/vercel.json).",
    )
    parser.add_argument(
        "--url",
        help="Explicit HTTPS backend tunnel URL, e.g. https://example.ngrok-free.app",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Try the runtime URL file first, then fall back to the local ngrok API.",
    )
    parser.add_argument(
        "--from-runtime-file",
        action="store_true",
        help="Read the backend tunnel URL from the runtime URL file.",
    )
    parser.add_argument(
        "--runtime-url-file",
        type=Path,
        default=DEFAULT_RUNTIME_URL_FILE,
        help="File containing the current backend tunnel URL.",
    )
    parser.add_argument(
        "--from-ngrok-api",
        action="store_true",
        help="Discover the HTTPS tunnel URL from the local ngrok API.",
    )
    parser.add_argument(
        "--ngrok-api-url",
        default=DEFAULT_NGROK_API_URL,
        help="Local ngrok API URL used with --from-ngrok-api.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Backend port to match when using --from-ngrok-api.",
    )
    return parser.parse_args()


def normalize_base_url(url: str) -> str:
    value = url.strip().rstrip("/")
    if not value.startswith("https://"):
        raise ValueError("Backend tunnel URL must start with https://")
    return value


def fetch_backend_url_from_ngrok(api_url: str, port: int) -> str:
    try:
        with urllib.request.urlopen(api_url, timeout=2) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(
            f"Could not read ngrok tunnels from {api_url}. "
            f"Make sure ngrok is running for backend port {port}."
        ) from error

    candidates: list[str] = []
    fallback: list[str] = []

    for tunnel in payload.get("tunnels", []):
        public_url = str(tunnel.get("public_url") or "").strip()
        config = tunnel.get("config") or {}
        addr = str(config.get("addr") or "").strip()

        if not public_url.startswith("https://"):
            continue

        fallback.append(public_url)

        if addr.endswith(f":{port}") or addr.endswith(f"//127.0.0.1:{port}") or addr.endswith(
            f"//localhost:{port}"
        ):
            candidates.append(public_url)

    if candidates:
        return normalize_base_url(candidates[0])
    if len(fallback) == 1:
        return normalize_base_url(fallback[0])

    raise RuntimeError(
        "Could not determine a unique HTTPS backend tunnel from ngrok. "
        "Pass --url explicitly."
    )


def fetch_backend_url_from_runtime_file(runtime_url_file: Path) -> str:
    try:
        value = runtime_url_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise RuntimeError(
            f"Could not read backend tunnel URL from {runtime_url_file}. "
            "Start the backend tunnel first."
        ) from error

    if not value:
        raise RuntimeError(
            f"Backend tunnel URL file {runtime_url_file} is empty. "
            "Start the backend tunnel first."
        )

    return normalize_base_url(value)


def probe_backend_url(base_url: str) -> None:
    target = f"{base_url}/health"
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            probe = subprocess.run(
                ["curl", "-fsS", "-k", "--max-time", "20", target],
                capture_output=True,
                text=True,
                check=True,
            )
            if probe.stdout.strip():
                return
            raise RuntimeError(f"Backend tunnel health probe for {target} returned an empty response.")
        except (subprocess.CalledProcessError, RuntimeError) as error:
            last_error = error
            time.sleep(1.2 * (attempt + 1))

    raise RuntimeError(
        f"Backend tunnel health probe failed for {target}. "
        "Make sure the backend and tunnel are still running."
    ) from last_error


def update_vercel_config(config_path: Path, backend_base_url: str) -> int:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    rewrites = data.get("rewrites")
    if not isinstance(rewrites, list):
        raise RuntimeError(f"{config_path} does not contain a rewrites array.")

    updated = 0
    for rewrite in rewrites:
        source = rewrite.get("source")
        if source in REWRITE_SUFFIXES:
            rewrite["destination"] = backend_base_url + REWRITE_SUFFIXES[source]
            updated += 1

    if updated != len(REWRITE_SUFFIXES):
        raise RuntimeError(
            f"Expected to update {len(REWRITE_SUFFIXES)} rewrites, updated {updated}."
        )

    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return updated


def main() -> int:
    args = parse_args()
    selected = [bool(args.url), bool(args.auto), bool(args.from_runtime_file), bool(args.from_ngrok_api)]
    if sum(selected) != 1:
        print(
            "Use exactly one of --url, --auto, --from-runtime-file, or --from-ngrok-api.",
            file=sys.stderr,
        )
        return 2

    try:
        if args.url:
            backend_base_url = normalize_base_url(args.url)
            probe_backend_url(backend_base_url)
        elif args.from_runtime_file:
            backend_base_url = fetch_backend_url_from_runtime_file(args.runtime_url_file)
            probe_backend_url(backend_base_url)
        elif args.from_ngrok_api:
            backend_base_url = fetch_backend_url_from_ngrok(args.ngrok_api_url, args.port)
            probe_backend_url(backend_base_url)
        else:
            try:
                backend_base_url = fetch_backend_url_from_runtime_file(args.runtime_url_file)
                probe_backend_url(backend_base_url)
            except RuntimeError:
                backend_base_url = fetch_backend_url_from_ngrok(args.ngrok_api_url, args.port)
                probe_backend_url(backend_base_url)
        updated = update_vercel_config(args.config, backend_base_url)
    except (RuntimeError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Updated {updated} rewrites in {args.config} to {backend_base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import time
