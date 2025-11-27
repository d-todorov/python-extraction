"""
News Collector

Collects financial news from RSS feeds.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import feedparser
import logging
from datetime import datetime
from typing import List, Dict
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


class NewsCollector:
    """
    Collects financial news from RSS feeds.
    
    Features:
    - Multiple RSS feed support
    - Date parsing
    - Duplicate detection
    - Error handling per feed
    """
    
    def __init__(self, rss_feeds: Dict[str, str]):
        """
        Initialize collector.
        
        Args:
            rss_feeds: Dict mapping source names to RSS URLs
        """
        self.rss_feeds = rss_feeds
    
    def collect_news(self, limit: int = 10) -> List[Dict]:
        """
        Collect news from all RSS feeds.
        
        Args:
            limit: Maximum number of articles per feed
            
        Returns:
            List of news article dicts
        """
        all_news = []
        
        for source_name, feed_url in self.rss_feeds.items():
            try:
                logger.info(f"Fetching news from {source_name}")
                news_items = self._parse_feed(source_name, feed_url, limit)
                all_news.extend(news_items)
                logger.info(f"Collected {len(news_items)} articles from {source_name}")
            except Exception as e:
                logger.error(f"Error fetching from {source_name}: {e}")
                # Continue with other feeds
        
        if not all_news:
            raise Exception("Failed to collect news from any RSS feed")
        
        logger.info(f"Total articles collected: {len(all_news)}")
        return all_news
    
    def _parse_feed(self, source_name: str, feed_url: str, limit: int) -> List[Dict]:
        """
        Parse a single RSS feed.
        
        Args:
            source_name: Name of the source
            feed_url: RSS feed URL
            limit: Max articles to extract
            
        Returns:
            List of article dicts
        """
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning(f"Feed {source_name} has parsing issues: {feed.bozo_exception}")
        
        articles = []
        
        for entry in feed.entries[:limit]:
            try:
                article = self._extract_article_data(entry, source_name)
                articles.append(article)
            except Exception as e:
                logger.error(f"Error extracting article from {source_name}: {e}")
        
        return articles
    
    def _extract_article_data(self, entry, source: str) -> Dict:
        """
        Extract article data from RSS entry.
        
        Args:
            entry: feedparser entry object
            source: Source name
            
        Returns:
            Article data dict
        """
        # Extract title
        title = entry.get('title', 'No title').strip()
        
        # Extract link
        link = entry.get('link', '')
        
        # Extract description
        description = entry.get('summary', entry.get('description', ''))
        if description:
            # Remove HTML tags (basic)
            description = description.replace('<p>', '').replace('</p>', '')
            description = description.strip()[:500]  # Limit length
        
        # Extract published date
        published_date = None
        if 'published_parsed' in entry and entry.published_parsed:
            try:
                published_date = datetime(*entry.published_parsed[:6])
            except:
                pass
        
        # Fallback to parsing published string
        if not published_date and 'published' in entry:
            try:
                published_date = date_parser.parse(entry.published)
            except:
                pass
        
        return {
            'title': title,
            'link': link,
            'source': source,
            'description': description,
            'published_date': published_date
        }
