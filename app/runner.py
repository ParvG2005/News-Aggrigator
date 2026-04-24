from typing import List
from .config import YOUTUBE_CHANNELS
from .scrapers.youtube import YouTubeScraper, ChannelVideo
from .scrapers.free_sources import FreeSourcesScraper, ExternalArticle
from .database.repository import Repository


def run_scrapers(hours: int = 24) -> dict:
    youtube_scraper = YouTubeScraper()
    free_sources_scraper = FreeSourcesScraper()
    repo = Repository()
    
    youtube_videos = []
    video_dicts = []
    for channel_id in YOUTUBE_CHANNELS:
        videos = youtube_scraper.get_latest_videos(channel_id, hours=hours)
        youtube_videos.extend(videos)
        video_dicts.extend([
            {
                "video_id": v.video_id,
                "title": v.title,
                "url": v.url,
                "channel_id": channel_id,
                "published_at": v.published_at,
                "description": v.description,
                "transcript": v.transcript
            }
            for v in videos
        ])
    
    if video_dicts:
        repo.bulk_create_youtube_videos(video_dicts)

    external_articles = free_sources_scraper.scrape(hours=hours)
    external_dicts = [
        {
            "guid": f"external:{a.guid}",
            "title": a.title,
            "url": a.url,
            "published_at": a.published_at,
            "description": a.description,
            "category": a.category,
        }
        for a in external_articles
    ]
    if external_dicts:
        repo.bulk_create_external_articles(external_dicts)
    
    return {
        "youtube": youtube_videos,
        "external": external_articles,
    }


if __name__ == "__main__":
    results = run_scrapers(hours=24)
    print(f"YouTube videos: {len(results['youtube'])}")
    print(f"External articles: {len(results['external'])}")

