import io
import logging
import httpx

from src.scrapers.base import BaseScraper, ScrapeResult

logger = logging.getLogger(__name__)


class PdfScraper(BaseScraper):
    async def scrape(self, url: str) -> ScrapeResult:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(response.content))
            except ImportError:
                try:
                    import PyPDF2 as pypdf2_mod
                    reader = pypdf2_mod.PdfReader(io.BytesIO(response.content))
                except ImportError:
                    return self._create_failed_result(url, "pypdf/PyPDF2 not installed — cannot extract PDF text")

            pages = []
            for page in reader.pages[:20]:
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(text.strip())

            content = "\n\n".join(pages)
            if not content.strip():
                return self._create_failed_result(url, "PDF contains no extractable text")

            title = url.rstrip("/").split("/")[-1].replace(".pdf", "").replace("-", " ").replace("_", " ").title()
            return ScrapeResult(url=url, title=title, content=content[:50_000], status="success")

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching PDF {url}: {e}")
            return self._create_failed_result(url, f"HTTP error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping PDF {url}: {e}")
            return self._create_failed_result(url, f"Unexpected error: {e}")
