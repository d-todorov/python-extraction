"""
Unit Tests for Financial Dashboard

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import Database
from src.processors.data_processor import DataProcessor
from src.collectors.exchange_rate_collector import ExchangeRateCollector
from src.collectors.news_collector import NewsCollector


class TestDatabase:
    """Test database operations."""
    
    def test_database_init(self, tmp_path):
        """Test database initialization."""
        db_path = tmp_path / "test.db"
        db = Database(str(db_path))
        db.init_database()
        
        assert db_path.exists()
        db.close()
    
    def test_insert_exchange_rate(self, tmp_path):
        """Test inserting exchange rate."""
        db = Database(str(tmp_path / "test.db"))
        db.init_database()
        
        db.insert_exchange_rate(
            currency_code='EUR',
            rate=0.5113,
            timestamp=datetime.now()
        )
        
        rates = db.get_latest_rates()
        assert len(rates) == 1
        assert rates[0]['currency_code'] == 'EUR'
        assert rates[0]['rate'] == 0.5113
        
        db.close()
    
    def test_insert_news(self, tmp_path):
        """Test inserting news."""
        db = Database(str(tmp_path / "test.db"))
        db.init_database()
        
        rows = db.insert_news(
            title='Test News',
            link='https://example.com/news1',
            source='test'
        )
        
        assert rows == 1
        
        news = db.get_recent_news(limit=10)
        assert len(news) == 1
        assert news[0]['title'] == 'Test News'
        
        db.close()
    
    def test_duplicate_news_ignored(self, tmp_path):
        """Test that duplicate news is ignored."""
        db = Database(str(tmp_path / "test.db"))
        db.init_database()
        
        # Insert first time
        rows1 = db.insert_news(
            title='Test News',
            link='https://example.com/news1',
            source='test'
        )
        
        # Insert duplicate
        rows2 = db.insert_news(
            title='Test News Updated',
            link='https://example.com/news1',  # Same link
            source='test'
        )
        
        assert rows1 == 1
        assert rows2 == 0  # Duplicate ignored
        
        db.close()


class TestDataProcessor:
    """Test data processor."""
    
    def test_validate_rate_data_valid(self):
        """Test rate validation with valid data."""
        processor = DataProcessor()
        
        data = {
            'currency_code': 'EUR',
            'rate': 0.5113
        }
        
        assert processor.validate_rate_data(data) is True
    
    def test_validate_rate_data_invalid(self):
        """Test rate validation with invalid data."""
        processor = DataProcessor()
        
        # Missing fields
        assert processor.validate_rate_data({}) is False
        
        # Invalid currency code
        assert processor.validate_rate_data({'currency_code': 'EU', 'rate': 0.5}) is False
        
        # Negative rate
        assert processor.validate_rate_data({'currency_code': 'EUR', 'rate': -0.5}) is False
    
    def test_validate_news_data_valid(self):
        """Test news validation with valid data."""
        processor = DataProcessor()
        
        data = {
            'title': 'Test News Article',
            'link': 'https://example.com/news',
            'source': 'test'
        }
        
        assert processor.validate_news_data(data) is True
    
    def test_validate_news_data_invalid(self):
        """Test news validation with invalid data."""
        processor = DataProcessor()
        
        # Missing fields
        assert processor.validate_news_data({}) is False
        
        # Short title
        assert processor.validate_news_data({
            'title': 'Hi',
            'link': 'https://example.com',
            'source': 'test'
        }) is False
        
        # Invalid link
        assert processor.validate_news_data({
            'title': 'Test News',
            'link': 'not-a-url',
            'source': 'test'
        }) is False
    
    def test_calculate_daily_change(self):
        """Test daily change calculation."""
        processor = DataProcessor()
        
        # Positive change
        change = processor.calculate_daily_change(1.05, 1.00)
        assert change == 0.05
        
        # Negative change
        change = processor.calculate_daily_change(0.95, 1.00)
        assert change == -0.05
        
        # No change
        change = processor.calculate_daily_change(1.00, 1.00)
        assert change == 0.0
    
    def test_process_exchange_rates(self):
        """Test processing exchange rates."""
        processor = DataProcessor()
        
        rates = {
            'EUR': 0.5113,
            'USD': 0.5556
        }
        
        processed = processor.process_exchange_rates(rates)
        
        assert len(processed) == 2
        assert processed[0]['currency_code'] in ['EUR', 'USD']
        assert 'timestamp' in processed[0]
        assert 'daily_change' in processed[0]
    
    def test_process_news(self):
        """Test processing news."""
        processor = DataProcessor()
        
        news_items = [
            {
                'title': 'Test News 1',
                'link': 'https://example.com/1',
                'source': 'TEST',
                'description': '  Description  '
            },
            {
                'title': 'Test News 2',
                'link': 'https://example.com/2',
                'source': 'test'
            }
        ]
        
        processed = processor.process_news(news_items)
        
        assert len(processed) == 2
        assert processed[0]['source'] == 'test'  # Normalized to lowercase
        assert processed[0]['description'] == 'Description'  # Trimmed


class TestExchangeRateCollector:
    """Test exchange rate collector."""
    
    def test_validate_response_valid(self):
        """Test response validation with valid data."""
        collector = ExchangeRateCollector(
            api_url='https://example.com',
            tracked_currencies=['EUR', 'USD']
        )
        
        data = {
            'rates': {
                'EUR': 0.5113,
                'USD': 0.5556
            }
        }
        
        assert collector._validate_response(data) is True
    
    def test_validate_response_invalid(self):
        """Test response validation with invalid data."""
        collector = ExchangeRateCollector(
            api_url='https://example.com',
            tracked_currencies=['EUR']
        )
        
        # Not a dict
        assert collector._validate_response([]) is False
        
        # Missing rates
        assert collector._validate_response({}) is False
        
        # Rates not a dict
        assert collector._validate_response({'rates': []}) is False


class TestNewsCollector:
    """Test news collector."""
    
    def test_extract_article_data(self):
        """Test extracting article data from RSS entry."""
        collector = NewsCollector(rss_feeds={})
        
        # Mock RSS entry
        class MockEntry:
            def __init__(self):
                self.data = {
                    'title': 'Test Article',
                    'link': 'https://example.com/article',
                    'summary': '<p>Test description</p>'
                }
            
            def get(self, key, default=None):
                return self.data.get(key, default)
            
            def __contains__(self, key):
                return key in self.data
        
        entry = MockEntry()
        article = collector._extract_article_data(entry, 'test')
        
        assert article['title'] == 'Test Article'
        assert article['link'] == 'https://example.com/article'
        assert article['source'] == 'test'
        assert 'Test description' in article['description']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
