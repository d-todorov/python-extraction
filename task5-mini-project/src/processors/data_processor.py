"""
Data Processor

Processes and validates collected data.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Processes and validates financial data.
    
    Features:
    - Data validation
    - Daily change calculation
    - Data normalization
    """
    
    def process_exchange_rates(self, rates: Dict[str, float], 
                               previous_rates: Optional[Dict[str, float]] = None) -> List[Dict]:
        """
        Process exchange rates.
        
        Args:
            rates: Current rates dict
            previous_rates: Previous rates for change calculation
            
        Returns:
            List of processed rate dicts
        """
        processed = []
        timestamp = datetime.now()
        
        for currency_code, rate in rates.items():
            # Validate
            if not self.validate_rate_data({'currency_code': currency_code, 'rate': rate}):
                logger.warning(f"Invalid rate data for {currency_code}, skipping")
                continue
            
            # Calculate daily change
            daily_change = None
            if previous_rates and currency_code in previous_rates:
                daily_change = self.calculate_daily_change(rate, previous_rates[currency_code])
            
            processed.append({
                'currency_code': currency_code,
                'rate': rate,
                'timestamp': timestamp,
                'daily_change': daily_change
            })
        
        logger.info(f"Processed {len(processed)} exchange rates")
        return processed
    
    def process_news(self, news_items: List[Dict]) -> List[Dict]:
        """
        Process news articles.
        
        Args:
            news_items: List of raw news dicts
            
        Returns:
            List of processed news dicts
        """
        processed = []
        
        for item in news_items:
            # Validate
            if not self.validate_news_data(item):
                logger.warning(f"Invalid news data: {item.get('title', 'No title')[:30]}, skipping")
                continue
            
            # Normalize
            normalized = {
                'title': item['title'].strip(),
                'link': item['link'].strip(),
                'source': item['source'].lower(),
                'description': item.get('description', '').strip() if item.get('description') else None,
                'published_date': item.get('published_date')
            }
            
            processed.append(normalized)
        
        logger.info(f"Processed {len(processed)} news articles")
        return processed
    
    def calculate_daily_change(self, current: float, previous: float) -> float:
        """
        Calculate daily change percentage.
        
        Args:
            current: Current rate
            previous: Previous rate
            
        Returns:
            Change as decimal (e.g., 0.02 for 2% increase)
        """
        if previous == 0:
            return 0.0
        
        change = (current - previous) / previous
        return round(change, 6)
    
    def validate_rate_data(self, data: Dict) -> bool:
        """
        Validate exchange rate data.
        
        Args:
            data: Rate data dict
            
        Returns:
            True if valid
        """
        # Check required fields
        if 'currency_code' not in data or 'rate' not in data:
            return False
        
        # Check currency code format
        if not isinstance(data['currency_code'], str) or len(data['currency_code']) != 3:
            return False
        
        # Check rate is positive number
        try:
            rate = float(data['rate'])
            if rate <= 0:
                return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    def validate_news_data(self, data: Dict) -> bool:
        """
        Validate news article data.
        
        Args:
            data: News data dict
            
        Returns:
            True if valid
        """
        # Check required fields
        required = ['title', 'link', 'source']
        for field in required:
            if field not in data or not data[field]:
                return False
        
        # Check title length
        if len(data['title']) < 5:
            return False
        
        # Check link format
        if not data['link'].startswith('http'):
            return False
        
        return True
