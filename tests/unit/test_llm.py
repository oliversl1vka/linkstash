import pytest
from pathlib import Path

from src.llm.base import LLMBase
from src.llm.evaluator import Evaluator
from src.llm.summarizer import Summarizer
from src.llm.categorizer import Categorizer
from src.llm.skill_evaluator import SkillEvaluator
from src.pipeline import PipelineResult

# --- Mock subclasses that override generate_response to avoid real API calls ---

class MockEvaluator(Evaluator):
    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
        summary = context.get("summary", "")
        if "relevant" in summary:
            return "notify"
        return "do not notify"

class MockSummarizer(Summarizer):
    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
        content = context.get("content", "")
        return f"Summary of: {content[:50]}"

class MockCategorizer(Categorizer):
    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
        summary = context.get("summary", "")
        if "AI" in summary:
            return "AI Tools & Open Source"
        return "Uncategorized"

class MockCategorizerWithQuotes(Categorizer):
    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
        return '"AI Tools & Open Source"'


class TemplateOnlyLLM(LLMBase):
    def __init__(self):
        pass


class FailingSkillEvaluator(SkillEvaluator):
    def __init__(self):
        pass

    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500, system_prompt_template_path: str | None = None, system_context: dict | None = None) -> str:
        raise RuntimeError("template failure")


# --- Evaluator Tests ---

@pytest.mark.asyncio
async def test_evaluator_relevant():
    evaluator = MockEvaluator()
    result = await evaluator.evaluate("This is a highly relevant summary about AI tools.")
    assert result is True

@pytest.mark.asyncio
async def test_evaluator_irrelevant():
    evaluator = MockEvaluator()
    result = await evaluator.evaluate("Just a random news article.")
    assert result is False

@pytest.mark.asyncio
async def test_evaluator_exact_match_only():
    """Ensure 'don't notify' is not a false positive."""
    class StrictMockEvaluator(Evaluator):
        async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
            return "don't notify"
    
    evaluator = StrictMockEvaluator()
    result = await evaluator.evaluate("Some content")
    # "don't notify" stripped/lowered is "don't notify" — does not equal "notify"
    assert result is False


# --- Summarizer Tests ---

@pytest.mark.asyncio
async def test_summarizer_returns_summary():
    summarizer = MockSummarizer()
    result = await summarizer.summarize("This is a long article about machine learning and transformers.")
    assert "Summary of:" in result
    assert "machine learning" in result

@pytest.mark.asyncio
async def test_summarizer_handles_empty_content():
    summarizer = MockSummarizer()
    result = await summarizer.summarize("")
    assert isinstance(result, str)


# --- Categorizer Tests ---

@pytest.mark.asyncio
async def test_categorizer_returns_category():
    categorizer = MockCategorizer()
    result = await categorizer.categorize("A new AI tool for code generation")
    assert result == "AI Tools & Open Source"

@pytest.mark.asyncio
async def test_categorizer_uncategorized_fallback():
    categorizer = MockCategorizer()
    result = await categorizer.categorize("Random cooking recipe")
    assert result == "Uncategorized"

@pytest.mark.asyncio
async def test_categorizer_strips_outer_quotes():
    categorizer = MockCategorizerWithQuotes()
    result = await categorizer.categorize("Some summary")
    assert result == "AI Tools & Open Source"


def test_load_template_leaves_json_braces_intact(tmp_path: Path):
    template_path = tmp_path / "prompt.md"
    template_path.write_text(
        'Title: {title}\nExample: {{"worth_creating": true, "name": "demo"}}\n',
        encoding="utf-8",
    )

    rendered = TemplateOnlyLLM()._load_template(str(template_path), {"title": "Demo"})

    assert "Title: Demo" in rendered
    assert '{"worth_creating": true, "name": "demo"}' in rendered


def test_load_template_does_not_unescape_braces_in_context_values(tmp_path: Path):
    """Double-braces inside a *substituted context value* must not be unescaped."""
    template_path = tmp_path / "prompt.md"
    template_path.write_text("Content: {content}\n", encoding="utf-8")

    rendered = TemplateOnlyLLM()._load_template(
        str(template_path), {"content": "{{not a placeholder}}"}
    )

    assert "{{not a placeholder}}" in rendered


@pytest.mark.asyncio
async def test_skill_evaluator_returns_skip_when_generation_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("USER_PROFILE", "Test profile")
    evaluator = FailingSkillEvaluator()

    result = await evaluator.evaluate_skill(
        PipelineResult(
            url="https://example.com/tool",
            title="Example Tool",
            summary="Useful workflow",
            category="AI Tools & Open Source",
            status="success",
            notify=False,
            scrape_content="Important reusable details",
        ),
        [],
    )

    assert result.worth_creating is False
    assert result.action == "skip"
