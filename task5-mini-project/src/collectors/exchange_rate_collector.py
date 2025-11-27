"""
Exchange Rate Collector

Collects exchange rates from API.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import requests
import logging
from datetime import datetime
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)


class ExchangeRateCollector:
    """
    Collects exchange rates from external API.
    
    Features:
    - Retry logic with exponential backoff
    - Response validation
    - Error handling
    """
    
    def __init__(self, api_url: str, tracked_currencies: list, base_currency: str = 'BGN'):
        """
        Initialize collector.
        
        Args:
            api_url: Exchange rate API URL
            tracked_currencies: List of currency codes to track
            base_currency: Base currency code
        """
        self.api_url = api_url
        self.tracked_currencies = tracked_currencies
        self.base_currency = base_currency
        self.max_retries = 3
        self.timeout = 10
    
    def collect_rates(self) -> Dict[str, float]:
        """
        Collect current exchange rates.
        
        Returns:
            Dict mapping currency codes to rates
            
        Raises:
            Exception: If collection fails after retries
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Fetching exchange rates (attempt {attempt + 1}/{self.max_retries})")
                
                response = self._fetch_from_api()
                
                if not self._validate_response(response):
                    raise ValueError("Invalid API response format")
                
                # Extract rates for tracked currencies
                rates = {}
                all_rates = response.get('rates', {})
                
                for currency in self.tracked_currencies:
                    if currency in all_rates:
                        rates[currency] = all_rates[currency]
                    else:
                        logger.warning(f"Currency {currency} not found in API response")
                
                logger.info(f"Successfully collected {len(rates)} exchange rates")
                return rates
                
            except Exception as e:
                logger.error(f"Error collecting rates (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries reached, giving up")
                    raise
    
    def _fetch_from_api(self) -> Dict:
        """
        Fetch data from exchange rate API.
        
        Returns:
            API response as dict
        """
        response = requests.get(self.api_url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def _validate_response(self, data: Dict) -> bool:
        """
        Validate API response structure.
        
        Args:
            data: API response data
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        if 'rates' not in data:
            return False
        
        if not isinstance(data['rates'], dict):
            return False
        
        return True
