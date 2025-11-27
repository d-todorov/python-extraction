"""
Main Entry Point

Orchestrates data collection, processing, and API server.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import sys
import logging
import argparse
import schedule
import time
from datetime import datetime
from pathlib import Path
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    DATABASE_PATH, LOG_FILE, LOG_LEVEL, UPDATE_INTERVAL_MINUTES,
    EXCHANGE_RATE_API_URL, TRACKED_CURRENCIES, RSS_FEEDS
)
from src.storage.database import Database
from src.collectors.exchange_rate_collector import ExchangeRateCollector
from src.collectors.news_collector import NewsCollector
from src.processors.data_processor import DataProcessor
from src.api.app import run_server

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def update_data():
    """
    Collect and process data from all sources.
    
    This function:
    1. Collects exchange rates
    2. Collects news from RSS feeds
    3. Processes and validates data
    4. Stores in database
    """
    logger.info("=" * 60)
    logger.info("Starting data update")
    logger.info("=" * 60)
    
    db = Database(DATABASE_PATH)
    processor = DataProcessor()
    
    try:
        # Collect exchange rates
        logger.info("Collecting exchange rates...")
        rate_collector = ExchangeRateCollector(
            api_url=EXCHANGE_RATE_API_URL,
            tracked_currencies=TRACKED_CURRENCIES
        )
        rates = rate_collector.collect_rates()
        
        # Get previous rates for change calculation
        previous_rates = {}
        for currency in TRACKED_CURRENCIES:
            prev_rate = db.get_previous_rate(currency)
            if prev_rate:
                previous_rates[currency] = prev_rate
        
        # Process rates
        processed_rates = processor.process_exchange_rates(rates, previous_rates)
        
        # Store rates
        for rate_data in processed_rates:
            db.insert_exchange_rate(
                currency_code=rate_data['currency_code'],
                rate=rate_data['rate'],
                timestamp=rate_data['timestamp'],
                daily_change=rate_data['daily_change']
            )
        
        # Update metadata
        db.update_metadata('last_rate_update', datetime.now().isoformat())
        logger.info(f"✅ Successfully updated {len(processed_rates)} exchange rates")
        
    except Exception as e:
        logger.error(f"❌ Error updating exchange rates: {e}")
    
    try:
        # Collect news
        logger.info("Collecting news from RSS feeds...")
        news_collector = NewsCollector(rss_feeds=RSS_FEEDS)
        news_items = news_collector.collect_news(limit=10)
        
        # Process news
        processed_news = processor.process_news(news_items)
        
        # Store news
        new_count = 0
        for news_data in processed_news:
            rows = db.insert_news(
                title=news_data['title'],
                link=news_data['link'],
                source=news_data['source'],
                description=news_data['description'],
                published_date=news_data['published_date']
            )
            new_count += rows
        
        # Update metadata
        db.update_metadata('last_news_update', datetime.now().isoformat())
        logger.info(f"✅ Successfully added {new_count} new articles (out of {len(processed_news)} collected)")
        
    except Exception as e:
        logger.error(f"❌ Error updating news: {e}")
    
    db.close()
    logger.info("=" * 60)
    logger.info("Data update completed")
    logger.info("=" * 60)


def init_database():
    """Initialize database with schema."""
    logger.info("Initializing database...")
    db = Database(DATABASE_PATH)
    db.init_database()
    db.close()
    logger.info("✅ Database initialized successfully")


def run_scheduler():
    """Run scheduler for automatic updates."""
    # Ensure DB is initialized
    init_database()
    
    logger.info(f"Starting scheduler (update every {UPDATE_INTERVAL_MINUTES} minutes)")
    
    # Schedule updates
    schedule.every(UPDATE_INTERVAL_MINUTES).minutes.do(update_data)
    
    # Run initial update
    update_data()
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


def run_with_scheduler():
    """Run API server with scheduler in background."""
    # Ensure DB is initialized
    init_database()
    
    logger.info("Starting API server with scheduler")
    
    # Run scheduler in background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Run API server in main thread
    run_server()


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(description='Financial Dashboard Pipeline')
    parser.add_argument('command', choices=['update', 'serve', 'schedule', 'init-db'],
                       help='Command to execute')
    
    args = parser.parse_args()
    
    if args.command == 'init-db':
        init_database()
    elif args.command == 'update':
        update_data()
    elif args.command == 'serve':
        run_server()
    elif args.command == 'schedule':
        run_with_scheduler()


if __name__ == '__main__':
    main()
