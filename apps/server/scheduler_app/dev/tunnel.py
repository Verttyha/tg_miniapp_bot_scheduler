from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Sequence
from urllib.parse import urlparse

from scheduler_app.settings import Settings

TRYCLOUDFLARE_URL_PATTERN = re.compile(r"https://[-a-z0-9]+\.trycloudflare\.com", re.IGNORECASE)
LOCALHOST_RUN_URL_PATTERN = re.compile(
    r"tunneled with tls termination,\s*(https://[^\s]+)",
    re.IGNORECASE,
)
DEFAULT_CLOUDFLARE_PROTOCOL = "http2" if os.name == "nt" else "quic"
DEFAULT_PROVIDER = "localhost-run"


def parse_args(
    argv: Sequence[str] | None = None,
    *,
    default_provider: str = DEFAULT_PROVIDER,
) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expose the local Telegram Scheduler service through a public HTTPS tunnel.",
    )
    parser.add_argument(
        "--provider",
        default=default_provider,
        choices=("localhost-run", "cloudflare"),
        help="Tunnel provider. Defaults to localhost.run because it is more reliable in this setup.",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Local service URL that should be published on the internet.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file where BASE_URL should be updated.",
    )
    parser.add_argument(
        "--ssh-bin",
        default="ssh",
        help="Path to the ssh executable used by localhost.run.",
    )
    parser.add_argument(
        "--cloudflared-bin",
        default="cloudflared",
        help="Path to the cloudflared executable used by the Cloudflare fallback.",
    )
    parser.add_argument(
        "--protocol",
        default=DEFAULT_CLOUDFLARE_PROTOCOL,
        choices=("auto", "quic", "http2"),
        help="Transport protocol for the Cloudflare fallback. Defaults to http2 on Windows, quic elsewhere.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def upsert_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False

    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_binary(binary_name: str, install_message: str) -> str:
    resolved = shutil.which(binary_name)
    if resolved:
        return resolved
    raise SystemExit(install_message)


def parse_local_service(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if not parsed.scheme:
        raise SystemExit(f"Unsupported URL '{url}'. Use a full URL such as http://127.0.0.1:8000.")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    if port is None:
        raise SystemExit(f"URL '{url}' does not include a port.")
    return host, port


def build_localhost_run_command(args: argparse.Namespace) -> list[str]:
    ssh_path = ensure_binary(
        args.ssh_bin,
        "ssh is not installed or not in PATH. Install OpenSSH Client, then rerun this command.",
    )
    host, port = parse_local_service(args.url)
    known_hosts_path = "NUL" if os.name == "nt" else "/dev/null"
    return [
        ssh_path,
        "-T",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={known_hosts_path}",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "ExitOnForwardFailure=yes",
        "-R",
        f"80:{host}:{port}",
        "nokey@localhost.run",
    ]


def build_cloudflare_command(args: argparse.Namespace) -> list[str]:
    cloudflared_path = ensure_binary(
        args.cloudflared_bin,
        "cloudflared is not installed or not in PATH. Install it first, then rerun this command.",
    )
    return [cloudflared_path, "tunnel", "--protocol", args.protocol, "--url", args.url]


def extract_public_url(provider: str, line: str) -> str | None:
    if provider == "cloudflare":
        match = TRYCLOUDFLARE_URL_PATTERN.search(line)
        return match.group(0) if match else None
    match = LOCALHOST_RUN_URL_PATTERN.search(line)
    return match.group(1) if match else None


def print_discovery_message(env_path: Path, discovered_url: str, settings: Settings | None) -> None:
    print(f"Updated {env_path} with BASE_URL={discovered_url}")
    print("Restart the backend if it is already running so it picks up the new public URL.")
    if settings and settings.sync_telegram_webhook_on_startup:
        print(
            "On next app startup, Telegram webhook will sync automatically to "
            f"{discovered_url}/webhooks/telegram"
        )
    else:
        print("SYNC_TELEGRAM_WEBHOOK_ON_STARTUP is disabled, so set the webhook manually if needed.")


def run_tunnel(args: argparse.Namespace) -> None:
    provider_name = "Cloudflare quick tunnel" if args.provider == "cloudflare" else "localhost.run tunnel"
    command = (
        build_cloudflare_command(args)
        if args.provider == "cloudflare"
        else build_localhost_run_command(args)
    )
    env_path = Path(args.env_file).resolve()

    try:
        settings = Settings(_env_file=env_path)
    except Exception:
        settings = None

    print(f"Starting {provider_name} for {args.url}")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    try:
        discovered_url: str | None = None
        if process.stdout is None:
            raise SystemExit(f"{provider_name} did not provide output for URL discovery.")

        for line in process.stdout:
            print(line, end="")
            if discovered_url is not None:
                continue

            discovered_url = extract_public_url(args.provider, line)
            if discovered_url is None:
                continue

            upsert_env_value(env_path, "BASE_URL", discovered_url)
            print_discovery_message(env_path, discovered_url, settings)

        return_code = process.wait()
        if discovered_url is None and return_code != 0:
            raise SystemExit(
                f"{provider_name} exited before publishing a public URL (exit code {return_code})."
            )
    except KeyboardInterrupt:
        print(f"\nStopping {provider_name.lower()}...")
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main(
    argv: Sequence[str] | None = None,
    *,
    default_provider: str = DEFAULT_PROVIDER,
) -> None:
    args = parse_args(argv, default_provider=default_provider)
    run_tunnel(args)


if __name__ == "__main__":
    main()
