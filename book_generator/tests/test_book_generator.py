import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from collect import collect_sources, notebook_to_text, parse_repo_url
from render import write_epub, write_pdf
from writer import write_book


def test_parse_repo_url():
    assert parse_repo_url("NirDiamant/RAG_Techniques")[1] == "RAG_Techniques"
    assert parse_repo_url("https://github.com/a/b.git")[0] == "https://github.com/a/b.git"
    with pytest.raises(ValueError):
        parse_repo_url("https://example.com/x")


def test_collect(tmp_path):
    (tmp_path / "README.md").write_text("# Hi")
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "x.py").write_text("no")
    nb = {"cells": [{"cell_type": "markdown", "source": ["# T"]},
                    {"cell_type": "code", "source": ["x=1"], "outputs": [{"big": 1}]}]}
    (tmp_path / "n.ipynb").write_text(json.dumps(nb))
    paths = [s.path for s in collect_sources(tmp_path)]
    assert paths == ["README.md", "n.ipynb", "a.py"]
    assert "x=1" in notebook_to_text(json.dumps(nb)) and "big" not in notebook_to_text(json.dumps(nb))


class FakeClient:
    def __init__(self):
        self.messages = self
        self.n = 0

    def create(self, **kw):
        self.n += 1
        if self.n == 1:
            t = json.dumps({"title": "T", "chapters": [{"title": "One", "summary": "s", "files": ["a.py"]}]})
        else:
            t = "# One\n\nText\n\n```python\nprint(1)\n```"
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)])


def test_pipeline_and_render(tmp_path):
    (tmp_path / "a.py").write_text("print(1)")
    title, chapters = write_book("r", collect_sources(tmp_path), client=FakeClient(), log=lambda *_: None)
    assert title == "T" and chapters[0].startswith("# One")
    write_epub(title, "me", chapters, tmp_path / "b.epub")
    write_pdf(title, "me", chapters, tmp_path / "b.pdf")
    assert (tmp_path / "b.epub").stat().st_size > 0
    assert (tmp_path / "b.pdf").read_bytes().startswith(b"%PDF")
