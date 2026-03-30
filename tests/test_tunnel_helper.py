from __future__ import annotations

from argparse import Namespace

from scheduler_app.dev.tunnel import build_localhost_run_command, extract_public_url, parse_local_service


def test_parse_local_service_extracts_host_and_port():
    assert parse_local_service("http://127.0.0.1:8000") == ("127.0.0.1", 8000)


def test_extract_public_url_for_localhost_run():
    line = "92b5b32151189d.lhr.life tunneled with tls termination, https://92b5b32151189d.lhr.life"
    assert extract_public_url("localhost-run", line) == "https://92b5b32151189d.lhr.life"


def test_build_localhost_run_command(monkeypatch):
    monkeypatch.setattr("scheduler_app.dev.tunnel.shutil.which", lambda name: rf"C:\Tools\{name}.exe")
    args = Namespace(
        url="http://127.0.0.1:8000",
        ssh_bin="ssh",
    )

    command = build_localhost_run_command(args)

    assert command[0] == r"C:\Tools\ssh.exe"
    assert "nokey@localhost.run" in command
    assert "-R" in command
    assert "80:127.0.0.1:8000" in command
