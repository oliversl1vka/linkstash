from dataclasses import dataclass
from abc import ABC, abstractmethod
from urllib.parse import urlparse

@dataclass
class ScrapeResult:
    url: str
    title: str
    content: str
    status: str  # "success", "partial", "failed"
    error_reason: str = ""

class BaseScraper(ABC):
    @abstractmethod
    async def scrape(self, url: str) -> ScrapeResult:
        """Scrapes the URL and returns a ScrapeResult."""
        pass
        
    def _create_failed_result(self, url: str, reason: str) -> ScrapeResult:
        return ScrapeResult(
            url=url,
            title="Unknown",
            content="",
            status="failed",
            error_reason=reason
        )

class UnsupportedFormatScraper(BaseScraper):
    async def scrape(self, url: str) -> ScrapeResult:
        return self._create_failed_result(url, "Unsupported URL format or extension")

def get_scraper_for_url(url: str) -> BaseScraper:
    """Factory to select the appropriate scraper based on the URL."""
    # We must import here to avoid circular dependencies if scrapers import BaseScraper
    from src.scrapers.article import ArticleScraper
    from src.scrapers.github import GitHubScraper
    from src.scrapers.notebook import NotebookScraper
    
    parsed = urlparse(url)
    
    # Route PDF URLs to PdfScraper
    if parsed.path.lower().endswith('.pdf'):
        from src.scrapers.pdf import PdfScraper
        return PdfScraper()

    # Block other unsupported binary formats
    unsupported_exts = ['.zip', '.exe', '.tar', '.gz', '.mp3', '.mp4']
    if any(parsed.path.lower().endswith(ext) for ext in unsupported_exts):
        return UnsupportedFormatScraper()
        
    if "github.com" in parsed.netloc:
        # Check if it's a blob/raw Jupyter notebook
        if url.endswith(".ipynb"):
            return NotebookScraper()
        # Route GitHub URLs with at least owner/repo to GitHubScraper
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) >= 2:
            return GitHubScraper()
            
    if url.endswith(".ipynb"):
        return NotebookScraper()
        
    return ArticleScraper()

