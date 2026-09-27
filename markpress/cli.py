"""Command-line entry point: `python -m markpress --src content --out public`."""
from __future__ import annotations

import argparse
import os
import sys

from markpress.generator import DEFAULT_SITE_TITLE, build_site


def build_info_from_env(environ=os.environ) -> str | None:
    """Describe the Jenkins build, if we are running inside one."""
    number = environ.get("BUILD_NUMBER")
    if not number:
        return None
    commit = environ.get("GIT_COMMIT", "")[:7]
    return f"Build #{number} (commit {commit})" if commit else f"Build #{number}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="markpress",
        description="Build a static website from a folder of Markdown files.",
    )
    parser.add_argument("--src", default="content", help="folder of .md files (default: content)")
    parser.add_argument("--out", default="public", help="output folder (default: public)")
    parser.add_argument("--title", default=DEFAULT_SITE_TITLE, help="site title")
    parser.add_argument("--drafts", action="store_true", help="include pages marked as drafts")
    args = parser.parse_args(argv)

    try:
        pages = build_site(
            args.src,
            args.out,
            site_title=args.title,
            include_drafts=args.drafts,
            build_info=build_info_from_env(),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Built {len(pages)} page(s) into {args.out}/")
    return 0
