import pytest
from src.llm.evaluator import Evaluator
from src.llm.summarizer import Summarizer
from src.llm.categorizer import Categorizer

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
