"""Render markdown chapters to EPUB and PDF."""
from __future__ import annotations

import html
from pathlib import Path

import markdown

CSS = """
body { font-family: Georgia, serif; line-height: 1.5; }
h1 { page-break-before: always; margin-top: 2em; }
pre { background: #f5f5f5; padding: .6em; white-space: pre-wrap; font-size: .8em; }
code { font-family: Menlo, Consolas, monospace; font-size: .9em; }
"""
MD_EXT = ["fenced_code", "tables", "sane_lists"]


def to_html(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=MD_EXT)


def write_epub(title: str, author: str, chapters: list[str], out: Path) -> None:
    from ebooklib import epub
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language("en")
    book.add_author(author)
    css = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=CSS)
    book.add_item(css)
    items = []
    for i, md_text in enumerate(chapters, 1):
        first = md_text.splitlines()[0].lstrip("# ").strip() if md_text else f"Chapter {i}"
        item = epub.EpubHtml(title=first, file_name=f"chap_{i:02d}.xhtml", lang="en")
        item.content = to_html(md_text)
        item.add_item(css)
        book.add_item(item)
        items.append(item)
    book.toc = items
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *items]
    epub.write_epub(str(out), book)


def write_pdf(title: str, author: str, chapters: list[str], out: Path) -> None:
    from weasyprint import HTML
    body = "".join(to_html(c) for c in chapters)
    doc = (f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
           f"<style>{CSS} .cover{{text-align:center;margin-top:30%}}</style></head><body>"
           f"<div class='cover'><h1 style='page-break-before:avoid'>{html.escape(title)}</h1>"
           f"<p>{html.escape(author)}</p></div>{body}</body></html>")
    HTML(string=doc).write_pdf(str(out))
