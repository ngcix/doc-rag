"""SpecRAG command-line entry point."""

from __future__ import annotations

import logging

from specrag.cli.commands import dispatch
from specrag.cli.parser import build_parser
from specrag.cli_output import configure_cli_output


def main() -> None:
    configure_cli_output()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    dispatch(parser.parse_args(), parser)
