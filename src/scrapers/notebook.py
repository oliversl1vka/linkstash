import httpx
import json
from src.scrapers.base import BaseScraper, ScrapeResult
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class NotebookScraper(BaseScraper):
    async def scrape(self, url: str) -> ScrapeResult:
        try:
            # Convert GitHub blob URLs to raw content URLs
            if "github.com" in url and "/blob/" in url:
                parsed = urlparse(url)
                # Only rewrite if it's actually github.com (not already raw)
                if parsed.netloc == "github.com":
                    raw_path = parsed.path.replace("/blob/", "/", 1)
                    url = f"https://raw.githubusercontent.com{raw_path}"
                
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                try:
                    notebook_data = response.json()
                except json.JSONDecodeError:
                    return self._create_failed_result(url, "URL does not point to valid JSON (ipynb)")
                    
            if 'cells' not in notebook_data:
                return self._create_failed_result(url, "JSON does not appear to be a Jupyter Notebook (missing 'cells')")
                
            title = url.split('/')[-1]
            
            extracted_content = []
            for cell in notebook_data['cells']:
                cell_type = cell.get('cell_type', '')
                source = "".join(cell.get('source', []))
                
                if not source.strip():
                    continue
                    
                if cell_type == 'markdown':
                    extracted_content.append(f"[MARKDOWN]\n{source}")
                elif cell_type == 'code':
                    extracted_content.append(f"[CODE]\n{source}")
                    
                    # Also extract text outputs if available
                    outputs = cell.get('outputs', [])
                    for out in outputs:
                        if out.get('output_type') == 'stream':
                            out_text = "".join(out.get('text', []))
                            if out_text.strip():
                                extracted_content.append(f"[OUTPUT]\n{out_text}")
                        elif 'data' in out and 'text/plain' in out['data']:
                            out_text = "".join(out['data']['text/plain'])
                            if out_text.strip():
                                extracted_content.append(f"[OUTPUT]\n{out_text}")

            full_content = "\n\n".join(extracted_content)
            
            if not full_content.strip():
                 return self._create_failed_result(url, "Notebook contains no readable markdown or code")
                 
            return ScrapeResult(
                url=url,
                title=title,
                content=full_content,
                status="success"
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error scraping Notebook {url}: {e}")
            return self._create_failed_result(url, f"HTTP Error: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error scraping Notebook {url}: {e}")
            return self._create_failed_result(url, f"Unexpected Error: {e}")
