from openai import AsyncOpenAI, APITimeoutError
import asyncio
from src.config import settings
from src.utils.logging import log_api_call
import logging

logger = logging.getLogger(__name__)

class LLMBase:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=60.0)
        self.model = settings.model_name
        
    async def generate_response(self, prompt_template_path: str, context: dict, max_tokens: int = 500) -> str:
        """Loads a prompt template, formats it, and calls the OpenAI API."""
        try:
            with open(prompt_template_path, "r", encoding="utf-8") as f:
                template = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt template not found: {prompt_template_path}")
            raise
            
        prompt = template.format(**context)
        
        # Truncate prompt if it risks exceeding context window (~100k chars ≈ ~25k tokens)
        max_prompt_chars = 100_000
        if len(prompt) > max_prompt_chars:
            logger.warning(f"Prompt truncated from {len(prompt)} to {max_prompt_chars} chars")
            prompt = prompt[:max_prompt_chars] + "\n\n[Content truncated due to length]"
        
        try:
            response = await self._call_openai(prompt, max_tokens)
            
            result_text = response.choices[0].message.content.strip()
            
            # Log the call
            log_api_call(
                model=self.model,
                prompt=prompt,
                response=result_text,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens
            )
            
            return result_text
            
        except Exception as e:
            logger.error(f"OpenAI API Error: {e}")
            raise

    async def _call_openai(self, prompt: str, max_tokens: int):
        """Call OpenAI API with one retry on timeout."""
        for attempt in range(2):
            try:
                return await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=max_tokens
                )
            except APITimeoutError:
                if attempt == 0:
                    logger.warning("OpenAI API timeout, retrying once...")
                    await asyncio.sleep(2)
                else:
                    raise
