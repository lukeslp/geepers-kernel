"""WSGI/CLI entrypoint for Dreamwalker when managed via service_manager."""
from __future__ import annotations

import os

from shared.web.dreamwalker.app import create_app


def main() -> None:
    app = create_app()
    port = int(os.getenv("PORT", os.getenv("DREAMWALKER_PORT", 5080)))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_ENV") == "development")


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    main()
