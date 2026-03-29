import httpx
import trafilatura
from src.scrapers.base import BaseScraper, ScrapeResult
import logging

logger = logging.getLogger(__name__)

class ArticleScraper(BaseScraper):
    async def scrape(self, url: str) -> ScrapeResult:
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
                
            # Extract content using trafilatura
            extracted_text = trafilatura.extract(html)
            
            if not extracted_text:
                return self._create_failed_result(url, "Trafilatura could not extract main content")
                
            # Attempt to extract title, fallback to URL
            metadata = trafilatura.extract_metadata(html)
            title = metadata.title if metadata and metadata.title else url
            
            return ScrapeResult(
                url=url,
                title=title,
                content=extracted_text,
                status="success"
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error while scraping {url}: {e}")
            return self._create_failed_result(url, f"HTTP Error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping {url}: {e}")
            return self._create_failed_result(url, f"Unexpected Error: {e}")
