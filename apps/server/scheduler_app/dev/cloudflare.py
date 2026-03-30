from __future__ import annotations

from scheduler_app.dev.tunnel import main as tunnel_main


def main() -> None:
    # Backward-compatible alias for environments where the old console script
    # is already installed. It now follows the default provider selection.
    tunnel_main()


if __name__ == "__main__":
    main()
