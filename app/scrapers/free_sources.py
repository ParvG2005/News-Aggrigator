from datetime import datetime, timedelta, timezone
from hashlib import sha1
import os
from typing import List, Optional

import feedparser
import requests
from pydantic import BaseModel


class ExternalArticle(BaseModel):
    guid: str
    title: str
    url: str
    published_at: datetime
    description: str
    category: Optional[str] = None


class FreeSourcesScraper:
    def __init__(self):
        self.cutoff = None
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ai-news-aggregator/1.0 (+https://github.com/)",
                "Accept": "application/json, text/plain, */*",
            }
        )
        self.rss_feeds = [
            ("openai-blog", "https://openai.com/news/rss.xml"),
            ("anthropic-news", "https://www.anthropic.com/news/rss.xml"),
            ("google-ai-blog", "https://blog.google/technology/ai/rss/"),
            ("nvidia-blog", "https://blogs.nvidia.com/blog/category/deep-learning/feed/"),
            ("venturebeat-ai", "https://venturebeat.com/ai/feed/"),
            ("ars-technica-ai", "https://feeds.arstechnica.com/arstechnica/technology-lab"),
            ("arxiv-cs-ai", "https://export.arxiv.org/rss/cs.AI"),
            ("arxiv-cs-lg", "https://export.arxiv.org/rss/cs.LG"),
        ]
        self.github_release_feeds = [
            ("github-openai-python", "https://github.com/openai/openai-python/releases.atom"),
            ("github-langchain", "https://github.com/langchain-ai/langchain/releases.atom"),
            ("github-vllm", "https://github.com/vllm-project/vllm/releases.atom"),
            ("github-llama-cpp", "https://github.com/ggerganov/llama.cpp/releases.atom"),
        ]
        self.reddit_subreddits = [
            "MachineLearning",
            "LocalLLaMA",
            "artificial",
            "singularity",
        ]
        self.ai_keywords = (
            "ai",
            "llm",
            "gpt",
            "anthropic",
            "openai",
            "gemini",
            "rag",
            "agent",
            "diffusion",
            "transformer",
        )
        self.max_total_articles = int(os.getenv("MAX_EXTERNAL_ARTICLES_TOTAL", "120"))
        self.max_per_source = int(os.getenv("MAX_EXTERNAL_ARTICLES_PER_SOURCE", "25"))
        self.max_hn_items = int(os.getenv("MAX_HN_ITEMS", "60"))
        self.max_reddit_items_per_subreddit = int(os.getenv("MAX_REDDIT_ITEMS_PER_SUBREDDIT", "25"))
        self.enable_reddit = os.getenv("ENABLE_REDDIT", "true").lower() in {"1", "true", "yes", "on"}
        self.enable_hackernews = os.getenv("ENABLE_HACKERNEWS", "true").lower() in {"1", "true", "yes", "on"}
        self.enable_github_releases = os.getenv("ENABLE_GITHUB_RELEASES", "true").lower() in {"1", "true", "yes", "on"}

    def scrape(self, hours: int = 24) -> List[ExternalArticle]:
        self.cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        collected: List[ExternalArticle] = []
        collected.extend(self._scrape_rss_feeds())
        if self.enable_github_releases:
            collected.extend(self._scrape_github_releases())
        if self.enable_hackernews:
            collected.extend(self._scrape_hacker_news())
        if self.enable_reddit:
            collected.extend(self._scrape_reddit())
        deduped = self._dedupe(collected)
        deduped.sort(key=lambda x: x.published_at, reverse=True)
        return deduped[: self.max_total_articles]

    def _scrape_rss_feeds(self) -> List[ExternalArticle]:
        output: List[ExternalArticle] = []
        for category, url in self.rss_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[: self.max_per_source]:
                    published = self._entry_published(entry)
                    if not published or published < self.cutoff:
                        continue
                    link = entry.get("link", "").strip()
                    title = entry.get("title", "").strip()
                    if not link or not title:
                        continue
                    output.append(
                        ExternalArticle(
                            guid=self._stable_guid(f"{category}:{link}"),
                            title=title,
                            url=link,
                            published_at=published,
                            description=self._clean_summary(entry.get("summary", "")),
                            category=category,
                        )
                    )
            except Exception:
                continue
        return output

    def _scrape_github_releases(self) -> List[ExternalArticle]:
        output: List[ExternalArticle] = []
        for category, url in self.github_release_feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[: self.max_per_source]:
                    published = self._entry_published(entry)
                    if not published or published < self.cutoff:
                        continue
                    link = entry.get("link", "").strip()
                    title = entry.get("title", "").strip()
                    if not link or not title:
                        continue
                    output.append(
                        ExternalArticle(
                            guid=self._stable_guid(f"{category}:{link}"),
                            title=title,
                            url=link,
                            published_at=published,
                            description=self._clean_summary(entry.get("summary", "")),
                            category=category,
                        )
                    )
            except Exception:
                continue
        return output

    def _scrape_hacker_news(self) -> List[ExternalArticle]:
        output: List[ExternalArticle] = []
        try:
            top_ids = self.session.get(
                "https://hacker-news.firebaseio.com/v0/topstories.json",
                timeout=10,
            ).json()
        except Exception:
            return output

        for story_id in top_ids[: self.max_hn_items]:
            try:
                item = self.session.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=10,
                ).json()
                if not item or item.get("type") != "story":
                    continue
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                title_lower = title.lower()
                if not any(keyword in title_lower for keyword in self.ai_keywords):
                    continue
                published = datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)
                if published < self.cutoff:
                    continue
                link = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                output.append(
                    ExternalArticle(
                        guid=self._stable_guid(f"hn:{story_id}:{link}"),
                        title=title,
                        url=link,
                        published_at=published,
                        description=f"Hacker News score: {item.get('score', 0)}",
                        category="hacker-news",
                    )
                )
            except Exception:
                continue
        return output

    def _scrape_reddit(self) -> List[ExternalArticle]:
        output: List[ExternalArticle] = []
        for subreddit in self.reddit_subreddits:
            try:
                data = self.session.get(
                    f"https://www.reddit.com/r/{subreddit}/new.json?limit=40",
                    timeout=10,
                ).json()
                posts = data.get("data", {}).get("children", [])
                picked = 0
                for post in posts:
                    post_data = post.get("data", {})
                    created = datetime.fromtimestamp(post_data.get("created_utc", 0), tz=timezone.utc)
                    if created < self.cutoff:
                        continue
                    title = (post_data.get("title") or "").strip()
                    if not title:
                        continue
                    title_lower = title.lower()
                    if not any(keyword in title_lower for keyword in self.ai_keywords):
                        continue
                    permalink = post_data.get("permalink", "")
                    link = f"https://www.reddit.com{permalink}" if permalink else ""
                    if not link:
                        continue
                    description = (post_data.get("selftext") or "").strip()
                    if len(description) > 600:
                        description = description[:597] + "..."
                    output.append(
                        ExternalArticle(
                            guid=self._stable_guid(f"reddit:{post_data.get('id', '')}:{link}"),
                            title=title,
                            url=link,
                            published_at=created,
                            description=description,
                            category=f"reddit-{subreddit.lower()}",
                        )
                    )
                    picked += 1
                    if picked >= self.max_reddit_items_per_subreddit:
                        break
            except Exception:
                continue
        return output

    def _entry_published(self, entry) -> Optional[datetime]:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            return None
        return datetime(*parsed[:6], tzinfo=timezone.utc)

    def _stable_guid(self, text: str) -> str:
        return sha1(text.encode("utf-8")).hexdigest()

    def _clean_summary(self, summary: str) -> str:
        value = " ".join((summary or "").split())
        return value[:1200]

    def _dedupe(self, items: List[ExternalArticle]) -> List[ExternalArticle]:
        deduped = {}
        for item in items:
            deduped[item.guid] = item
        return list(deduped.values())
