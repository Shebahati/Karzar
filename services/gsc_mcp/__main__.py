from __future__ import annotations

import logging

from services.gsc_mcp.config import get_settings
from services.gsc_mcp.server import run_streamable_http

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main() -> None:
    run_streamable_http(get_settings())


if __name__ == "__main__":
    main()
