#!/usr/bin/env python3
"""Bootstrap and run the local Telegram Mini App stack."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = REPO_ROOT / ".venv"
ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"
ENV_FILE = REPO_ROOT / ".env"
REQUIREMENTS_FILE = REPO_ROOT / "requirements.txt"
RUNTIME_DIR = REPO_ROOT / ".codex-runtime"
RUNTIME_URL_FILE = RUNTIME_DIR / "backend-tunnel-url.txt"
INSTALL_STAMP_FILE = VENV_DIR / ".requirements.sha256"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap or run the local Telegram Mini App stack.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        help="Prepare .env, .venv, Python dependencies, and database migrations.",
    )
    bootstrap_parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create the virtual environment.",
    )
    bootstrap_parser.add_argument(
        "--force-install",
        action="store_true",
        help="Reinstall Python dependencies even if requirements.txt did not change.",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Start backend, public tunnel, and optionally the Telegram bot.",
    )
    run_parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to create the virtual environment when needed.",
    )
    run_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Local backend host to bind.",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Local backend port to expose.",
    )
    run_parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Assume .env, .venv, dependencies, and migrations are already ready.",
    )
    run_parser.add_argument(
        "--force-install",
        action="store_true",
        help="Reinstall Python dependencies before launch.",
    )
    run_parser.add_argument(
        "--skip-bot",
        action="store_true",
        help="Do not start the Telegram polling bot.",
    )
    return parser.parse_args()


def print_step(message: str) -> None:
    print(f"[tg-miniapp] {message}", flush=True)


def env_file_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        normalized_key = key.strip()
        normalized_value = value.strip()
        if len(normalized_value) >= 2 and normalized_value[0] == normalized_value[-1] and normalized_value[0] in {"'", '"'}:
            normalized_value = normalized_value[1:-1]
        values[normalized_key] = normalized_value

    return values


def resolve_env_value(key: str) -> str:
    runtime_value = os.environ.get(key)
    if runtime_value is not None:
        return runtime_value.strip()
    return env_file_values(ENV_FILE).get(key, "").strip()


def ensure_env_file() -> None:
    if ENV_FILE.exists():
        return

    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    print_step(f"Created {ENV_FILE.name} from {ENV_EXAMPLE_FILE.name}")


def venv_python_path() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=REPO_ROOT, env=env, check=True)


def requirements_hash() -> str:
    payload = REQUIREMENTS_FILE.read_bytes() + b"\n" + sys.version.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ensure_venv(python_executable: str) -> Path:
    python_path = venv_python_path()
    if python_path.exists():
        return python_path

    print_step(f"Creating virtual environment with {python_executable}")
    run_command([python_executable, "-m", "venv", str(VENV_DIR)])
    return python_path


def ensure_dependencies(python_path: Path, *, force_install: bool) -> None:
    current_hash = requirements_hash()
    recorded_hash = ""
    if INSTALL_STAMP_FILE.exists():
        recorded_hash = INSTALL_STAMP_FILE.read_text(encoding="utf-8").strip()

    if not force_install and recorded_hash == current_hash:
        print_step("Python dependencies are already up to date")
        return

    print_step("Installing Python dependencies")
    run_command([str(python_path), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])
    INSTALL_STAMP_FILE.write_text(current_hash + "\n", encoding="utf-8")


def run_migrations(python_path: Path) -> None:
    print_step("Running database migrations")
    try:
        run_command([str(python_path), "-m", "alembic", "upgrade", "head"])
    except subprocess.CalledProcessError as exc:
        database_url = resolve_env_value("DATABASE_URL")
        normalized_url = database_url.lower()
        if normalized_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            raise RuntimeError(
                "Could not connect to PostgreSQL for migrations. "
                "Start PostgreSQL and create the database configured in DATABASE_URL before bootstrap."
            ) from exc
        raise


def bootstrap(python_executable: str, *, force_install: bool) -> Path:
    ensure_env_file()
    python_path = ensure_venv(python_executable)
    ensure_dependencies(python_path, force_install=force_install)
    run_migrations(python_path)
    return python_path


def healthcheck_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/health"


def ensure_port_is_free(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        if sock.connect_ex((host, port)) == 0:
            raise RuntimeError(
                f"Port {port} on {host} is already in use. "
                "Stop the existing process or rerun with a different port."
            )


def wait_for_backend(host: str, port: int, process: subprocess.Popen[str], *, timeout_seconds: float = 45.0) -> None:
    target = healthcheck_url(host, port)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend exited early with code {process.returncode}.")

        try:
            with urllib.request.urlopen(target, timeout=1.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)

    raise RuntimeError(f"Backend did not become healthy at {target} within {timeout_seconds:.0f}s.")


def read_public_url(url_file: Path) -> str:
    if not url_file.exists():
        return ""
    return url_file.read_text(encoding="utf-8").strip()


def wait_for_public_url(url_file: Path, process: subprocess.Popen[str], *, timeout_seconds: float = 60.0) -> str:
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tunnel process exited early with code {process.returncode}.")

        public_url = read_public_url(url_file)
        if public_url.startswith("https://"):
            return public_url

        time.sleep(0.5)

    raise RuntimeError(f"Public tunnel URL was not written to {url_file} within {timeout_seconds:.0f}s.")


def start_process(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    return subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )


def resolve_bot_username() -> str:
    return resolve_env_value("TELEGRAM_BOT_USERNAME").lstrip("@")


def print_runtime_summary(public_url: str, *, bot_started: bool) -> None:
    print_step(f"Mini App URL: {public_url}")

    bot_username = resolve_bot_username()
    if bot_started and bot_username:
        print_step(f"Open the bot: https://t.me/{bot_username}")
        print_step(f"Direct Mini App link: https://t.me/{bot_username}/app")
    elif bot_started:
        print_step("Telegram bot started. Open your bot chat and send /start.")
    else:
        print_step("Telegram bot was not started. Set TELEGRAM_BOT_TOKEN in .env to launch it automatically.")

    print_step("Press Ctrl+C to stop backend, tunnel, and bot.")


def shutdown_processes(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()

    deadline = time.time() + 8
    while time.time() < deadline:
        if all(process.poll() is not None for process in processes):
            return
        time.sleep(0.2)

    for process in processes:
        if process.poll() is None:
            process.kill()


def run_stack(args: argparse.Namespace) -> int:
    python_path = venv_python_path()
    if args.skip_bootstrap:
        if not python_path.exists():
            raise RuntimeError(".venv is missing. Run bootstrap first or remove --skip-bootstrap.")
    else:
        python_path = bootstrap(args.python, force_install=args.force_install)

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if RUNTIME_URL_FILE.exists():
        RUNTIME_URL_FILE.unlink()

    backend_env = os.environ.copy()
    backend_env["PYTHONUNBUFFERED"] = "1"

    ensure_port_is_free(args.host, args.port)

    print_step("Starting FastAPI backend")
    backend_process = start_process(
        [
            str(python_path),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ],
        env=backend_env,
    )

    processes = [backend_process]

    try:
        wait_for_backend(args.host, args.port, backend_process)
        print_step("Backend is healthy")

        print_step("Starting public localhost.run tunnel")
        tunnel_process = start_process(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "start_localhost_run_tunnel.py"),
                "--port",
                str(args.port),
                "--url-file",
                str(RUNTIME_URL_FILE),
            ],
            env=os.environ.copy(),
        )
        processes.append(tunnel_process)

        public_url = wait_for_public_url(RUNTIME_URL_FILE, tunnel_process)

        bot_started = False
        if args.skip_bot:
            print_step("Skipping Telegram bot start because --skip-bot was passed")
        elif not resolve_env_value("TELEGRAM_BOT_TOKEN"):
            print_step("TELEGRAM_BOT_TOKEN is empty, so the Telegram bot was skipped")
        else:
            print_step("Starting Telegram bot polling")
            bot_env = os.environ.copy()
            bot_env["MINIAPP_PUBLIC_URL"] = public_url
            bot_env["PYTHONUNBUFFERED"] = "1"
            bot_process = start_process(
                [str(python_path), str(REPO_ROOT / "scripts" / "telegram_bot.py")],
                env=bot_env,
            )
            processes.append(bot_process)
            bot_started = True

        print_runtime_summary(public_url, bot_started=bot_started)

        while True:
            for process in processes:
                return_code = process.poll()
                if return_code is None:
                    continue
                if process is backend_process:
                    raise RuntimeError(f"Backend stopped with code {return_code}.")
                if process is tunnel_process:
                    raise RuntimeError(f"Tunnel stopped with code {return_code}.")
                raise RuntimeError(f"Telegram bot stopped with code {return_code}.")
            time.sleep(0.7)
    except KeyboardInterrupt:
        print_step("Stopping local Telegram Mini App stack")
        return 130
    finally:
        shutdown_processes(processes)


def main() -> int:
    args = parse_args()
    try:
        if args.command == "bootstrap":
            bootstrap(args.python, force_install=args.force_install)
            print_step("Local bootstrap is ready")
            return 0
        return run_stack(args)
    except subprocess.CalledProcessError as error:
        print_step(f"Command failed with code {error.returncode}: {' '.join(error.cmd)}")
        return error.returncode
    except RuntimeError as error:
        print_step(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
