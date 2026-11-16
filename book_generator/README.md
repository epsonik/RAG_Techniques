# book_generator

CLI that turns a GitHub repo into a book (EPUB / PDF / Markdown). Claude plans the outline from the repo's files, then writes each chapter from the relevant sources.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
python book_gen.py NirDiamant/RAG_Techniques --formats epub pdf --max-chapters 12
python book_gen.py ./local/dir -o out --formats md
```

Notebook outputs are dropped; only markdown and code cells are read. Each chapter's source files are capped (20k chars/file, ~400k chars/chapter). Cost scales with chapter count. Run tests with `pytest tests`.
