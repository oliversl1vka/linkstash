import os
from pathlib import Path
from src.llm.base import LLMBase

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Evaluator(LLMBase):
    async def evaluate(self, summary: str) -> bool:
        """Evaluates relevance based on user profile and returns True to notify, False otherwise."""

        user_profile = os.environ.get("USER_PROFILE")
        if not user_profile:
            profile_path = _PROJECT_ROOT / "user_profile.md"
            try:
                user_profile = profile_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                user_profile = "No user profile found."
            
        context = {
            "user_profile": user_profile,
            "summary": summary
        }
        
        result = await self.generate_response("prompts/evaluate.md", context, max_tokens=10)
        
        result = result.strip().strip("'").lower()
        return result == "notify"
