# LinkStash — Project Guidelines

Personal link management bot: Telegram → scrape → LLM (summarize, categorize, evaluate) → Markdown storage.

## Architecture

```
Telegram Bot (bot.py)
  └→ Pipeline (pipeline.py): Ingest → Duplicate Check → Scrape → Summarize → Categorize → Evaluate → Store
       ├→ Scrapers (scrapers/): ArticleScraper, GitHubScraper, NotebookScraper — selected by factory in base.py
       ├→ LLM modules (llm/): Summarizer, Categorizer, Evaluator — all extend LLMBase (AsyncOpenAI)
       ├→ Storage (storage/writer.py): Markdown files in data/, prepend-only (newest first)
       └→ Prompts (prompts/*.md): Template files with {placeholders} for LLM context
```

- **Config**: `config.yaml` loaded by `src/config.py` → `settings` singleton. Env vars override YAML values.
- **User profile**: `user_profile.md` at project root — read by Summarizer and Evaluator to tailor output.
- **Specs**: `specs/001-linkstash-core/` contains the feature spec, tasks, and checklists.

## Code Style

- Python 3.11+. Type hints on all function signatures and return types.
- Async/await for all I/O: scrapers use `httpx.AsyncClient`, LLM uses `AsyncOpenAI`, bot uses `python-telegram-bot` async handlers.
- ABC base classes for scrapers (`BaseScraper`) and shared LLM logic (`LLMBase`).
- Factory pattern: `get_scraper_for_url()` in `src/scrapers/base.py` — uses late imports to avoid circular deps.
- Structured results via dataclasses: `ScrapeResult`, `PipelineResult`, `Config`.
- Logging: `logger = logging.getLogger(__name__)` per module. API calls logged in `src/utils/logging.py`.

## Build and Test

```bash
# Install
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

# Run bot
python src/bot.py

# Run tests
pytest tests/

# Lint
ruff check .
```

## Conventions

- **Imports**: Absolute (`from src.config import settings`). Standard lib → third-party → project. Late imports in factories.
- **Naming**: PascalCase classes, snake_case functions, UPPERCASE constants, `_prefix` for private methods.
- **Scraper pattern**: Subclass `BaseScraper`, implement `async def scrape(self, url: str) -> ScrapeResult`. Use `_create_failed_result()` for errors.
- **LLM pattern**: Subclass `LLMBase`, call `self.generate_response(prompt_path, context_dict, max_tokens)`. Prompt templates live in `prompts/`.
- **Storage**: All data in `data/` as Markdown. Category names sanitized to filenames. Entries prepended (newest first).
- **Testing**: `pytest` + `pytest-asyncio`. Unit tests mock LLM via subclass override. Integration tests monkey-patch pipeline functions. Fixtures use `autouse=True` with setup/teardown for file cleanup.
- **Error handling**: Each pipeline step catches exceptions and returns result objects with status fields (`"success"`, `"failed"`, `"duplicate"`). No bare `except:`.
- **Bot security**: Only `telegram_user_id` from config is allowed to interact.
