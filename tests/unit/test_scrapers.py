import pytest
from src.scrapers.base import ScrapeResult, BaseScraper, get_scraper_for_url, UnsupportedFormatScraper
from src.scrapers.github import GitHubScraper
from src.scrapers.notebook import NotebookScraper
from src.scrapers.article import ArticleScraper
from src.scrapers.pdf import PdfScraper


# --- BaseScraper Tests ---

@pytest.mark.asyncio
async def test_base_scraper_failed_result():
    class DummyScraper(BaseScraper):
        async def scrape(self, url: str) -> ScrapeResult:
            return self._create_failed_result(url, "test_failure")
            
    scraper = DummyScraper()
    result = await scraper.scrape("http://example.com")
    
    assert result.status == "failed"
    assert result.error_reason == "test_failure"
    assert result.url == "http://example.com"


# --- Scraper Factory Tests ---

def test_factory_returns_article_for_normal_url():
    scraper = get_scraper_for_url("https://example.com/article/123")
    assert isinstance(scraper, ArticleScraper)

def test_factory_returns_github_for_repo_url():
    scraper = get_scraper_for_url("https://github.com/owner/repo")
    assert isinstance(scraper, GitHubScraper)

def test_factory_returns_github_for_deep_repo_url():
    scraper = get_scraper_for_url("https://github.com/owner/repo/tree/main/src")
    assert isinstance(scraper, GitHubScraper)

def test_factory_returns_notebook_for_ipynb():
    scraper = get_scraper_for_url("https://github.com/owner/repo/blob/main/notebook.ipynb")
    assert isinstance(scraper, NotebookScraper)

def test_factory_returns_notebook_for_non_github_ipynb():
    scraper = get_scraper_for_url("https://example.com/data/analysis.ipynb")
    assert isinstance(scraper, NotebookScraper)

def test_factory_returns_pdf_scraper_for_pdf():
    scraper = get_scraper_for_url("https://example.com/paper.pdf")
    assert isinstance(scraper, PdfScraper)

def test_factory_returns_unsupported_for_zip():
    scraper = get_scraper_for_url("https://example.com/archive.zip")
    assert isinstance(scraper, UnsupportedFormatScraper)


# --- GitHubScraper Tests ---

@pytest.mark.asyncio
async def test_github_scraper_invalid_url():
    scraper = GitHubScraper()
    result = await scraper.scrape("https://github.com/invalid") # Missing repo
    assert result.status == "failed"
    assert "Invalid GitHub repository" in result.error_reason


# --- NotebookScraper Tests ---

@pytest.mark.asyncio
async def test_notebook_scraper_invalid_json():
    scraper = NotebookScraper()
    result = await scraper.scrape("https://example.com")
    assert result.status == "failed"


# --- ArticleScraper Tests ---

@pytest.mark.asyncio
async def test_article_scraper_invalid_url():
    scraper = ArticleScraper()
    result = await scraper.scrape("https://this-domain-does-not-exist-xyz123.com")
    assert result.status == "failed"
    assert result.error_reason  # Should have a reason

@pytest.mark.asyncio
async def test_unsupported_format_scraper():
    scraper = UnsupportedFormatScraper()
    result = await scraper.scrape("https://example.com/file.pdf")
    assert result.status == "failed"
    assert "Unsupported" in result.error_reason
