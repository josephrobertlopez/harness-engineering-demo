"""Command-line interface for specgate."""

import argparse
import sys
from specgate import __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="specgate",
        description="Specification gate for PRD validation",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"specgate {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("check", help="Check a PRD against schema")

    args = parser.parse_args()

    if args.command == "check":
        print("not implemented", file=sys.stderr)
        sys.exit(2)

    # If no command provided, print help
    if args.command is None:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
