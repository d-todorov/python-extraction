# Task 2: API Integration

Robust REST API client for fetching exchange rates with retry logic and caching.

## Features

- ✅ Exponential backoff retry (3 attempts)
- ✅ 1-hour caching
- ✅ Response validation
- ✅ Timeout handling
- ✅ Rate limiting (1 second delay)
- ✅ Comprehensive error messages

## Quick Start

```bash
cd task2-api-integration
pip install -r requirements.txt
python example_usage.py
```

## Usage

```python
from api_client import ExchangeRateClient

# Initialize client
client = ExchangeRateClient(base_currency='BGN')

# Get specific currencies
rates = client.get_rates(['EUR', 'USD', 'GBP'])
print(rates)
# {'EUR': 0.5113, 'USD': 0.5556, 'GBP': 0.4348}

# Get all available currencies
all_rates = client.get_rates()

# Clear cache to force fresh API call
client.clear_cache()
```

## Features Explained

### Retry Logic
- Retries up to 3 times on failure
- Exponential backoff: 1s, 2s, 4s
- Handles network errors gracefully

### Caching
- Caches responses for 1 hour
- Saves to `cache.json`
- Significantly faster for repeated calls

### Rate Limiting
- 1 second delay between API calls
- Prevents overwhelming the API

## API Endpoint

Uses: `https://api.exchangerate-api.com/v4/latest/{currency}`

## Testing

```bash
python -m pytest tests.py -v
```

## Technologies

- **requests** - HTTP client
- **retrying** - Retry logic with exponential backoff

## Author

API Integration Task  
Date: 2025-11-25
