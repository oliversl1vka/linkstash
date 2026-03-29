import os
from pathlib import Path
from src.llm.base import LLMBase

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Summarizer(LLMBase):
    async def summarize(self, content: str) -> str:
        """Summarizes the content using the user profile as context."""

        user_profile = os.environ.get("USER_PROFILE")
        if not user_profile:
            profile_path = _PROJECT_ROOT / "user_profile.md"
            try:
                user_profile = profile_path.read_text(encoding="utf-8")
            except FileNotFoundError:
                user_profile = "No user profile found."

        context = {
            "user_profile": user_profile,
            "content": content
        }

        return await self.generate_response(str(_PROJECT_ROOT / "prompts" / "summarize.md"), context)
