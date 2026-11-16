"""Fetch a GitHub repo and turn its files into text 'sources' an LLM can read."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
             ".idea", ".vscode", "images", "img", "assets", "static", "vendor"}
TEXT_EXTS = {".md", ".rst", ".txt", ".py", ".ipynb", ".js", ".ts", ".tsx", ".go", ".rs",
             ".java", ".c", ".cpp", ".h", ".rb", ".sh", ".toml", ".yaml", ".yml", ".json"}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "poetry.lock", "uv.lock"}
MAX_FILE_CHARS = 20_000


@dataclass
class Source:
    path: str       # repo-relative
    text: str       # content, truncated
    kind: str       # "doc" | "notebook" | "code" | "config"


def parse_repo_url(url: str) -> tuple[str, str]:
    """Return (clone_url, repo_name) for a GitHub URL or owner/repo shorthand."""
    m = re.match(r"^(?:https?://github\.com/|git@github\.com:)?([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url.strip())
    if not m:
        raise ValueError(f"Not a GitHub repo URL or owner/repo: {url!r}")
    owner, name = m.groups()
    return f"https://github.com/{owner}/{name}.git", name


def clone(url: str, dest: Path | None = None) -> Path:
    clone_url, name = parse_repo_url(url)
    dest = dest or Path(tempfile.mkdtemp(prefix="bookgen_")) / name
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", clone_url, str(dest)], check=True)
    return dest


def notebook_to_text(raw: str) -> str:
    """Markdown cells and code cells only; outputs are dropped (large, noisy)."""
    nb = json.loads(raw)
    parts = []
    for cell in nb.get("cells", []):
        src = "".join(cell.get("source", []))
        if not src.strip():
            continue
        parts.append(src if cell["cell_type"] == "markdown" else f"```python\n{src}\n```")
    return "\n\n".join(parts)


def _kind(p: Path) -> str:
    if p.suffix == ".ipynb":
        return "notebook"
    if p.suffix in {".md", ".rst", ".txt"}:
        return "doc"
    if p.suffix in {".toml", ".yaml", ".yml", ".json"}:
        return "config"
    return "code"


def collect_sources(root: Path) -> list[Source]:
    out: list[Source] = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or p.name in SKIP_NAMES or p.suffix not in TEXT_EXTS:
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in rel.parts[:-1]):
            continue
        try:
            text = p.read_text(encoding="utf-8")
            if p.suffix == ".ipynb":
                text = notebook_to_text(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if text.strip():
            out.append(Source(rel.as_posix(), text[:MAX_FILE_CHARS], _kind(p)))
    # docs first, then notebooks, then code, then config; stable within kind
    order = {"doc": 0, "notebook": 1, "code": 2, "config": 3}
    return sorted(out, key=lambda s: (order[s.kind], s.path))


def render_sources(sources: list[Source]) -> str:
    return "\n\n".join(f"=== FILE: {s.path} ===\n{s.text}" for s in sources)
