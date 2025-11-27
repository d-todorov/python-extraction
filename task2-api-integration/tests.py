"""
Unit Tests for Exchange Rate API Client

Tests all core functionality including API requests, caching,
retry logic, and error handling.

Author: API Integration Tests
Date: 2025-11-25
"""

import pytest
import json
import os
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open
from api_client import ExchangeRateClient
import requests


@pytest.fixture
def client():
    """Create a test client instance."""
    return ExchangeRateClient(base_currency='BGN', cache_file='test_cache.json')


@pytest.fixture
def sample_api_response():
    """Sample API response data."""
    return {
        'base': 'BGN',
        'date': '2025-11-25',
        'rates': {
            'EUR': 0.51,
            'USD': 0.56,
            'GBP': 0.43,
            'JPY': 65.32
        }
    }


@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up test cache file after each test."""
    yield
    # Cleanup
    if os.path.exists('test_cache.json'):
        os.remove('test_cache.json')
    if os.path.exists('test_cache.json.tmp'):
        os.remove('test_cache.json.tmp')


class TestInitialization:
    """Test client initialization."""
    
    def test_default_initialization(self):
        """Test initialization with default parameters."""
        client = ExchangeRateClient()
        assert client.base_currency == 'BGN'
        assert client.cache_file == 'cache.json'
        assert client.cache_validity_hours == 1
        assert client.rate_limit_delay == 1
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        client = ExchangeRateClient(base_currency='EUR', cache_file='custom.json')
        assert client.base_currency == 'EUR'
        assert client.cache_file == 'custom.json'
        assert 'EUR' in client.api_url
    
    def test_currency_uppercase(self):
        """Test that currency is converted to uppercase."""
        client = ExchangeRateClient(base_currency='bgn')
        assert client.base_currency == 'BGN'


class TestCaching:
    """Test caching functionality."""
    
    def test_save_and_load_cache(self, client, sample_api_response):
        """Test saving and loading cache."""
        # Save cache
        client._save_cache(sample_api_response)
        
        # Verify file exists
        assert os.path.exists(client.cache_file)
        
        # Load cache
        cached_data = client._load_cache()
        
        # Verify structure
        assert 'timestamp' in cached_data
        assert 'data' in cached_data
        assert cached_data['data'] == sample_api_response
    
    def test_cache_validity_fresh(self, client, sample_api_response):
        """Test cache validity with fresh cache."""
        # Save cache
        client._save_cache(sample_api_response)
        
        # Check validity immediately
        assert client._is_cache_valid() is True
    
    def test_cache_validity_stale(self, client):
        """Test cache validity with stale cache."""
        # Create stale cache (2 hours old)
        stale_time = datetime.now() - timedelta(hours=2)
        cache_data = {
            'timestamp': stale_time.isoformat(),
            'data': {'rates': {}}
        }
        
        with open(client.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Check validity
        assert client._is_cache_valid() is False
    
    def test_cache_validity_no_file(self, client):
        """Test cache validity when file doesn't exist."""
        assert client._is_cache_valid() is False
    
    def test_cache_validity_no_timestamp(self, client):
        """Test cache validity with missing timestamp."""
        # Create cache without timestamp
        cache_data = {'data': {'rates': {}}}
        
        with open(client.cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Check validity
        assert client._is_cache_valid() is False
    
    def test_clear_cache(self, client, sample_api_response):
        """Test cache clearing."""
        # Save cache
        client._save_cache(sample_api_response)
        assert os.path.exists(client.cache_file)
        
        # Clear cache
        client.clear_cache()
        assert not os.path.exists(client.cache_file)
    
    def test_clear_cache_nonexistent(self, client):
        """Test clearing cache when file doesn't exist."""
        # Should not raise error
        client.clear_cache()


class TestAPIRequests:
    """Test API request functionality."""
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_success(self, mock_get, client, sample_api_response):
        """Test successful API fetch."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Fetch from API
        data = client._fetch_from_api()
        
        # Verify
        assert data == sample_api_response
        mock_get.assert_called_once()
        assert 'timeout' in mock_get.call_args.kwargs
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_timeout(self, mock_get, client):
        """Test API fetch with timeout."""
        # Mock timeout
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        # Should raise timeout error after retries
        with pytest.raises(requests.Timeout):
            client._fetch_from_api()
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_http_error(self, mock_get, client):
        """Test API fetch with HTTP error."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        
        # Create HTTPError with response attached
        http_error = requests.HTTPError("Server error")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        # Should raise HTTP error after retries
        with pytest.raises(requests.HTTPError):
            client._fetch_from_api()
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_rate_limit(self, mock_get, client):
        """Test API fetch with rate limit error."""
        # Mock rate limit error (429)
        mock_response = Mock()
        mock_response.status_code = 429
        
        # Create HTTPError with response attached
        http_error = requests.HTTPError("Rate limit")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        # Should raise HTTP error after retries
        with pytest.raises(requests.HTTPError):
            client._fetch_from_api()
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_invalid_json(self, mock_get, client):
        """Test API fetch with invalid JSON response."""
        # Mock invalid JSON
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            client._fetch_from_api()
    
    @patch('api_client.requests.get')
    def test_fetch_from_api_missing_rates(self, mock_get, client):
        """Test API fetch with missing rates field."""
        # Mock response without rates
        mock_response = Mock()
        mock_response.json.return_value = {'base': 'BGN'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            client._fetch_from_api()


class TestGetRates:
    """Test get_rates functionality."""
    
    @patch('api_client.requests.get')
    def test_get_rates_specific_currencies(self, mock_get, client, sample_api_response):
        """Test getting specific currencies."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Get specific currencies
        rates = client.get_rates(['EUR', 'USD'])
        
        # Verify
        assert 'EUR' in rates
        assert 'USD' in rates
        assert 'GBP' not in rates
        assert len(rates) == 2
    
    @patch('api_client.requests.get')
    def test_get_rates_all_currencies(self, mock_get, client, sample_api_response):
        """Test getting all currencies."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Get all currencies
        rates = client.get_rates()
        
        # Verify
        assert len(rates) == 4
        assert 'EUR' in rates
        assert 'USD' in rates
        assert 'GBP' in rates
        assert 'JPY' in rates
    
    @patch('api_client.requests.get')
    def test_get_rates_invalid_currency(self, mock_get, client, sample_api_response):
        """Test getting invalid currency."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Try to get invalid currency
        with pytest.raises(ValueError):
            client.get_rates(['XYZ'])
    
    @patch('api_client.requests.get')
    def test_get_rates_mixed_valid_invalid(self, mock_get, client, sample_api_response):
        """Test getting mix of valid and invalid currencies."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Get mix of valid and invalid
        rates = client.get_rates(['EUR', 'XYZ', 'USD'])
        
        # Should return only valid currencies
        assert 'EUR' in rates
        assert 'USD' in rates
        assert 'XYZ' not in rates
        assert len(rates) == 2
    
    @patch('api_client.requests.get')
    def test_get_rates_uses_cache(self, mock_get, client, sample_api_response):
        """Test that get_rates uses cache when valid."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # First call - fetches from API
        rates1 = client.get_rates(['EUR'])
        assert mock_get.call_count == 1
        
        # Second call - should use cache
        rates2 = client.get_rates(['EUR'])
        assert mock_get.call_count == 1  # No additional API call
        
        # Verify same data
        assert rates1 == rates2
    
    @patch('api_client.requests.get')
    def test_get_rates_case_insensitive(self, mock_get, client, sample_api_response):
        """Test that currency codes are case-insensitive."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Get with lowercase
        rates = client.get_rates(['eur', 'usd'])
        
        # Verify
        assert 'EUR' in rates
        assert 'USD' in rates


class TestRetryLogic:
    """Test retry logic."""
    
    @patch('api_client.requests.get')
    def test_retry_on_failure(self, mock_get, client, sample_api_response):
        """Test that API calls are retried on failure."""
        # Mock: fail twice, then succeed
        mock_response_fail = Mock()
        http_error = requests.HTTPError("Error")
        http_error.response = mock_response_fail
        mock_response_fail.raise_for_status.side_effect = http_error
        
        mock_response_success = Mock()
        mock_response_success.json.return_value = sample_api_response
        mock_response_success.raise_for_status = Mock()
        
        mock_get.side_effect = [
            mock_response_fail,
            mock_response_fail,
            mock_response_success
        ]
        
        # Should succeed after retries
        data = client._fetch_from_api()
        assert data == sample_api_response
        assert mock_get.call_count == 3


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_rates_response(self, client):
        """Test handling of empty rates."""
        with patch('api_client.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {'rates': {}}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            rates = client.get_rates()
            assert rates == {}
    
    def test_corrupted_cache_file(self, client):
        """Test handling of corrupted cache file."""
        # Create corrupted cache
        with open(client.cache_file, 'w') as f:
            f.write("invalid json{{{")
        
        # Should return False for validity
        assert client._is_cache_valid() is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
