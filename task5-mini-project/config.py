"""
Configuration for Financial Dashboard

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Environment (set via ENV variable: development/production)
ENV = os.getenv('ENV', 'development')

# Database
DATABASE_PATH = 'data/financial_data.db'

# Logging
LOG_LEVEL = 'DEBUG' if ENV == 'development' else 'INFO'
LOG_FILE = 'logs/app.log'

# API
API_HOST = '0.0.0.0'
API_PORT = int(os.getenv('PORT', 5000))

# Update interval (minutes) - Daily updates
UPDATE_INTERVAL_MINUTES = 1440  # 24 hours

# Exchange Rate API
EXCHANGE_RATE_API_URL = 'https://api.exchangerate-api.com/v4/latest/BGN'
TRACKED_CURRENCIES = ['EUR', 'USD', 'GBP']

# RSS Feeds (ONLY these sources - verified working)
RSS_FEEDS = {
    'capital': 'https://www.capital.bg/rss/',
    'bnb': 'https://www.bnb.bg/AboutUs/PressOffice/PORSS/index.htm?getRSS=1&lang=BG&cat=2',
    'economic': 'https://www.economic.bg/rss/ikonomika.xml'
}

# API Rate Limits
MAX_HISTORY_DAYS = 7
DEFAULT_HISTORY_DAYS = 1
MAX_NEWS_LIMIT = 10
DEFAULT_NEWS_LIMIT = 1
