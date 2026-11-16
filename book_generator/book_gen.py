#!/usr/bin/env python3
"""Generate a book (EPUB/PDF) from a GitHub repository using Claude.

    export ANTHROPIC_API_KEY=...
    python book_gen.py NirDiamant/RAG_Techniques --formats epub pdf
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from collect import clone, collect_sources, parse_repo_url
from render import write_epub, write_pdf
from writer import DEFAULT_MODEL, write_book


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "book"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", help="GitHub URL, owner/repo, or a local directory")
    ap.add_argument("-o", "--out-dir", default="output")
    ap.add_argument("--formats", nargs="+", choices=["epub", "pdf", "md"], default=["epub", "pdf"])
    ap.add_argument("--max-chapters", type=int, default=12)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--author", default="Generated with Claude")
    args = ap.parse_args(argv)

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("error: set ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    local = Path(args.repo)
    if local.is_dir():
        root, name = local.resolve(), local.resolve().name
    else:
        name = parse_repo_url(args.repo)[1]
        print(f"Cloning {args.repo} ...")
        root = clone(args.repo)

    sources = collect_sources(root)
    if not sources:
        print("error: no readable files found", file=sys.stderr)
        return 1
    print(f"Collected {len(sources)} files")

    title, chapters = write_book(name, sources, args.max_chapters, args.model)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = out / slug(title)
    if "md" in args.formats:
        base.with_suffix(".md").write_text("\n\n".join(chapters), encoding="utf-8")
    if "epub" in args.formats:
        write_epub(title, args.author, chapters, base.with_suffix(".epub"))
    if "pdf" in args.formats:
        write_pdf(title, args.author, chapters, base.with_suffix(".pdf"))
    print(f"Done. Files in {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
