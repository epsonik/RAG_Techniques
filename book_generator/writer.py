"""Use Claude to plan an outline and write each chapter."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from collect import Source, render_sources

DEFAULT_MODEL = "claude-sonnet-5-5"
CONTEXT_CHAR_BUDGET = 400_000   # ~100k tokens of repo material per call


@dataclass
class Chapter:
    title: str
    summary: str
    files: list[str]


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def _extract_json(s: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    return json.loads(m.group(1) if m else s)


def _fit(sources: list[Source], budget: int) -> list[Source]:
    chosen, used = [], 0
    for s in sources:
        if used + len(s.text) > budget:
            continue
        chosen.append(s)
        used += len(s.text)
    return chosen


def plan_book(client, sources: list[Source], repo_name: str, max_chapters: int, model: str) -> tuple[str, list[Chapter]]:
    listing = "\n".join(f"- {s.path} ({s.kind}, {len(s.text)} chars)" for s in sources[:600])
    readme = next((s for s in sources if s.path.lower().startswith("readme")), None)
    prompt = (
        f"You are planning a book that teaches the contents of the GitHub repo '{repo_name}'.\n\n"
        f"File listing:\n{listing}\n\n"
        f"README:\n{readme.text if readme else '(none)'}\n\n"
        f"Design a book of at most {max_chapters} chapters, in a sensible learning order. "
        "Each chapter covers a coherent topic and lists the repo files it draws from (exact paths from the listing). "
        'Reply with ONLY JSON: {"title": str, "chapters": [{"title": str, "summary": str, "files": [str]}]}'
    )
    resp = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
    data = _extract_json(_text(resp))
    return data["title"], [Chapter(c["title"], c["summary"], c.get("files", [])) for c in data["chapters"]][:max_chapters]


def write_chapter(client, ch: Chapter, idx: int, total: int, book_title: str,
                  sources: list[Source], model: str) -> str:
    by_path = {s.path: s for s in sources}
    picked = _fit([by_path[f] for f in ch.files if f in by_path], CONTEXT_CHAR_BUDGET)
    prompt = (
        f"You are writing chapter {idx} of {total} of the book '{book_title}', based on a GitHub repo.\n"
        f"Chapter: {ch.title}\nFocus: {ch.summary}\n\n"
        f"Source material:\n{render_sources(picked) or '(none)'}\n\n"
        "Write the chapter in Markdown as flowing, instructive prose: motivate the idea, explain how the code "
        "works, include the most important code excerpts in fenced blocks, and end with key takeaways. "
        "Only state what the sources support; do not invent APIs or results. "
        f"Start with a single '# {ch.title}' heading, then use '##' for sections. Output only the chapter."
    )
    resp = client.messages.create(model=model, max_tokens=8000, messages=[{"role": "user", "content": prompt}])
    return _text(resp).strip()


def write_book(repo_name: str, sources: list[Source], max_chapters: int = 12,
               model: str = DEFAULT_MODEL, log=print, client=None) -> tuple[str, list[str]]:
    client = client or anthropic.Anthropic()
    title, chapters = plan_book(client, sources, repo_name, max_chapters, model)
    log(f"Outline: '{title}', {len(chapters)} chapters")
    texts = []
    for i, ch in enumerate(chapters, 1):
        log(f"Writing chapter {i}/{len(chapters)}: {ch.title}")
        texts.append(write_chapter(client, ch, i, len(chapters), title, sources, model))
    return title, texts
