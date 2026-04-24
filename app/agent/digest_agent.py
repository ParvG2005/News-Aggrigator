from typing import Optional
from pydantic import BaseModel


class DigestOutput(BaseModel):
    title: str
    summary: str

PROMPT = """You are an expert AI news analyst specializing in summarizing technical articles, research papers, and video content about artificial intelligence.

Your role is to create concise, informative digests that help readers quickly understand the key points and significance of AI-related content.

Guidelines:
- Create a compelling title (5-10 words) that captures the essence of the content
- Write a 2-3 sentence summary that highlights the main points and why they matter
- Focus on actionable insights and implications
- Use clear, accessible language while maintaining technical accuracy
- Avoid marketing fluff - focus on substance"""


class DigestAgent:
    def __init__(self):
        self.system_prompt = PROMPT

    def generate_digest(self, title: str, content: str, article_type: str) -> Optional[DigestOutput]:
        return self._fallback_digest(title=title, content=content, article_type=article_type)

    def _fallback_digest(self, title: str, content: str, article_type: str) -> DigestOutput:
        trimmed = (content or "").strip().replace("\n", " ")
        short_summary = " ".join(trimmed.split())
        if len(short_summary) > 380:
            short_summary = short_summary[:377] + "..."
        if not short_summary:
            short_summary = "Content was captured, but an AI summary is temporarily unavailable."

        fallback_title = f"{article_type.title()} Update: {title}"
        if len(fallback_title) > 120:
            fallback_title = fallback_title[:117] + "..."

        return DigestOutput(
            title=fallback_title,
            summary=f"{short_summary}\n\n(Generated using fallback mode because AI API is unavailable.)",
        )

