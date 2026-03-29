from src.llm.base import LLMBase

class Categorizer(LLMBase):
    async def categorize(self, summary: str) -> str:
        """Categorizes the content based on its summary."""
        
        context = {
            "summary": summary
        }
        
        result = await self.generate_response("prompts/categorize.md", context, max_tokens=50)
        
        # Cleanup the response: strip whitespace, then remove matched outer quotes
        result = result.strip()
        if (result.startswith('"') and result.endswith('"')) or (result.startswith("'") and result.endswith("'")):
            result = result[1:-1]
        return result.strip()
