"""
Exchange Rate API Client

A robust API client for fetching exchange rates with caching, retry logic,
and comprehensive error handling.

Author: API Integration
Date: 2025-11-25
"""

import requests
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from retrying import retry
import os


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExchangeRateClient:
    """
    Client for fetching exchange rates from Exchangerate-API.
    
    Features:
    - Automatic caching with 1-hour validity
    - Retry logic with exponential backoff
    - Rate limiting
    - Comprehensive error handling
    """
    
    def __init__(self, base_currency: str = 'BGN', cache_file: str = 'cache.json'):
        """
        Initialize the exchange rate client.
        
        Args:
            base_currency: Base currency for exchange rates (default: BGN)
            cache_file: Path to cache file (default: cache.json)
        """
        self.base_currency = base_currency.upper()
        self.cache_file = cache_file
        self.api_url = f"https://api.exchangerate-api.com/v4/latest/{self.base_currency}"
        self.cache_validity_hours = 1
        self.rate_limit_delay = 1  # seconds between API calls
        
        logger.info(f"Initialized ExchangeRateClient for {self.base_currency}")
    
    def get_rates(self, currencies: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Get exchange rates for specified currencies.
        
        If cache is valid (< 1 hour old), returns cached data.
        Otherwise, fetches fresh data from API.
        
        Args:
            currencies: List of currency codes to retrieve (e.g., ['EUR', 'USD', 'GBP'])
                       If None, returns all available rates
        
        Returns:
            Dictionary mapping currency codes to exchange rates
            
        Raises:
            requests.RequestException: If API request fails after retries
            ValueError: If invalid currency codes are provided
        """
        logger.info(f"Requesting rates for currencies: {currencies or 'all'}")
        
        # Check if cache is valid
        if self._is_cache_valid():
            logger.info("Using cached data")
            cached_data = self._load_cache()
            rates = cached_data.get('data', {}).get('rates', {})
        else:
            logger.info("Cache invalid or missing, fetching from API")
            # Rate limiting - wait before making API call
            time.sleep(self.rate_limit_delay)
            
            # Fetch from API with retry logic
            data = self._fetch_from_api()
            rates = data.get('rates', {})
            
            # Save to cache
            self._save_cache(data)
        
        # Filter currencies if specified
        if currencies:
            currencies_upper = [c.upper() for c in currencies]
            filtered_rates = {}
            
            for currency in currencies_upper:
                if currency in rates:
                    filtered_rates[currency] = rates[currency]
                else:
                    logger.warning(f"Currency {currency} not found in rates")
            
            if not filtered_rates:
                raise ValueError(f"None of the requested currencies {currencies} were found")
            
            return filtered_rates
        
        return rates
    
    @retry(
        stop_max_attempt_number=3,
        wait_exponential_multiplier=1000,
        wait_exponential_max=10000
    )
    def _fetch_from_api(self) -> Dict:
        """
        Fetch exchange rate data from API with retry logic.
        
        Retries up to 3 times with exponential backoff:
        - 1st retry: wait 1 second
        - 2nd retry: wait 2 seconds
        - 3rd retry: wait 4 seconds (max 10 seconds)
        
        Returns:
            API response data as dictionary
            
        Raises:
            requests.HTTPError: If HTTP error occurs
            requests.Timeout: If request times out
            requests.RequestException: For other request errors
            ValueError: If response is not valid JSON
        """
        logger.info(f"Fetching data from API: {self.api_url}")
        
        try:
            # Make request with 10-second timeout
            response = requests.get(self.api_url, timeout=10)
            
            # Raise exception for HTTP errors (4xx, 5xx)
            response.raise_for_status()
            
            # Parse JSON response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                raise ValueError(f"API returned invalid JSON: {e}")
            
            # Validate response structure
            if 'rates' not in data:
                logger.error("API response missing 'rates' field")
                raise ValueError("Invalid API response structure")
            
            logger.info(f"Successfully fetched rates for {len(data.get('rates', {}))} currencies")
            return data
            
        except requests.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Rate limit exceeded (429)")
            else:
                logger.error(f"HTTP error {e.response.status_code}: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """
        Check if cached data is valid (less than 1 hour old).
        
        Returns:
            True if cache exists and is valid, False otherwise
        """
        if not os.path.exists(self.cache_file):
            logger.debug("Cache file does not exist")
            return False
        
        try:
            cached_data = self._load_cache()
            
            # Check if timestamp exists
            if 'timestamp' not in cached_data:
                logger.debug("Cache missing timestamp")
                return False
            
            # Parse timestamp
            cache_time = datetime.fromisoformat(cached_data['timestamp'])
            current_time = datetime.now()
            
            # Check if cache is within validity period
            age = current_time - cache_time
            is_valid = age < timedelta(hours=self.cache_validity_hours)
            
            if is_valid:
                logger.debug(f"Cache is valid (age: {age.total_seconds():.0f} seconds)")
            else:
                logger.debug(f"Cache is stale (age: {age.total_seconds():.0f} seconds)")
            
            return is_valid
            
        except Exception as e:
            logger.warning(f"Error checking cache validity: {e}")
            return False
    
    def _load_cache(self) -> Dict:
        """
        Load data from cache file.
        
        Returns:
            Cached data as dictionary
            
        Raises:
            FileNotFoundError: If cache file doesn't exist
            json.JSONDecodeError: If cache file contains invalid JSON
        """
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.debug("Successfully loaded cache")
            return data
        except FileNotFoundError:
            logger.debug("Cache file not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in cache file: {e}")
            raise
    
    def _save_cache(self, data: Dict) -> None:
        """
        Save data to cache file with timestamp.
        
        Args:
            data: API response data to cache
        """
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        try:
            # Atomic write: write to temp file first, then rename
            temp_file = f"{self.cache_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            # Rename temp file to actual cache file (atomic on most systems)
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            os.rename(temp_file, self.cache_file)
            
            logger.info(f"Saved data to cache: {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            raise
    
    def clear_cache(self) -> None:
        """
        Clear the cache file.
        
        Useful for forcing a fresh API call or testing.
        """
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
                logger.info("Cache cleared")
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")
                raise
        else:
            logger.info("Cache file does not exist, nothing to clear")


if __name__ == '__main__':
    # Simple test
    client = ExchangeRateClient()
    
    try:
        # Get specific currencies
        rates = client.get_rates(['EUR', 'USD', 'GBP'])
        print(f"\nExchange rates for BGN:")
        for currency, rate in rates.items():
            print(f"  1 BGN = {rate:.4f} {currency}")
    except Exception as e:
        print(f"Error: {e}")
