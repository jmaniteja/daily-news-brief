from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from .core import load_config
from .generator import generate
from .site import build_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="news-brief")
    parser.add_argument("--config", type=Path, default=Path("config.yml"))
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--date", type=date.fromisoformat)
    sub.add_parser("build")
    sub.add_parser("validate")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    root = args.config.resolve().parent
    if args.command == "validate":
        print(f"Configuration valid: {len(config['sources'])} sources")
    elif args.command == "build":
        print(build_site(root))
    else:
        print(generate(config, root, args.date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
