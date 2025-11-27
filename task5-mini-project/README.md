- News archiving

✅ **REST API**
- 4 endpoints: rates, history, news, health
- Query parameters for filtering
- Error handling

✅ **Web Dashboard**
- Real-time rate display
- 7-day history chart (Chart.js)
- Recent news feed
- Auto-refresh every 5 minutes

✅ **Scheduler**
- Automatic hourly updates
- Background processing
- Error recovery

## Quick Start

### 1. Install Dependencies

```bash
cd task5-mini-project
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
python main.py init-db
```

### 3. Run One-Time Update

```bash
python main.py update
```

### 4. Start API Server

```bash
python main.py serve
```

Visit: http://localhost:5000

### 5. Run with Scheduler (Recommended)

```bash
python main.py schedule
```

This starts the API server AND runs automatic updates every hour.

## Project Structure

```
task5-mini-project/
├── src/
│   ├── collectors/
│   │   ├── exchange_rate_collector.py  # Exchange rate API
│   │   └── news_collector.py           # RSS feed parser
│   ├── processors/
│   │   └── data_processor.py           # Validation & normalization
│   ├── storage/
│   │   ├── database.py                 # SQLite wrapper
│   │   └── models.py                   # Data models
│   └── api/
│       └── app.py                      # Flask REST API
├── static/
│   ├── css/style.css                   # Dashboard styles
│   └── js/dashboard.js                 # Dashboard logic
├── templates/
│   └── index.html                      # Dashboard UI
├── tests/
│   └── test_*.py                       # Unit tests
├── data/
│   └── financial_data.db               # SQLite database
├── logs/
│   └── app.log                         # Application logs
├── config.py                           # Configuration
├── main.py                             # Entry point
├── requirements.txt                    # Dependencies
└── README.md                           # This file
```

## API Endpoints

### GET /api/rates
Get current exchange rates.

**Response:**
```json
{
  "base_currency": "BGN",
  "timestamp": "2025-11-26T19:00:00",
  "rates": {
    "EUR": 0.5113,
    "USD": 0.5556,
    "GBP": 0.4348
  }
}
```

### GET /api/rates/history?days=7
Get historical rates (max 7 days, default 1).

**Response:**
```json
{
  "base_currency": "BGN",
  "days": 7,
  "history": [
    {
      "date": "2025-11-26",
      "rates": {
        "EUR": {"rate": 0.5113, "change": 0.0012},
        "USD": {"rate": 0.5556, "change": -0.0008}
      }
    }
  ]
}
```

### GET /api/news?limit=10
Get recent news (max 10, default 1).

**Response:**
```json
{
  "count": 10,
  "news": [
    {
      "id": 1,
      "title": "BNB announces new policy",
      "description": "...",
      "link": "https://...",
      "source": "bnb",
      "published_date": "2025-11-26T12:00:00"
    }
  ]
}
```

### GET /api/health
Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "last_rate_update": "2025-11-26T19:00:00",
  "last_news_update": "2025-11-26T19:00:00",
  "uptime_seconds": 3600
}
```

## Configuration

Edit `config.py` or set environment variables:

```python
# Database
DATABASE_PATH = 'data/financial_data.db'

# API
API_HOST = '0.0.0.0'
API_PORT = 5000

# Update interval
UPDATE_INTERVAL_MINUTES = 60

# Tracked currencies
TRACKED_CURRENCIES = ['EUR', 'USD', 'GBP']

# RSS Feeds
RSS_FEEDS = {
    'capital': 'https://www.capital.bg/rss/',
    'bnb': 'https://www.bnb.bg/...',
    'economic': 'https://www.economic.bg/rss/ikonomika.xml'
}
```

## Database Schema

### exchange_rates
- id (INTEGER PRIMARY KEY)
- currency_code (TEXT)
- rate (REAL)
- base_currency (TEXT)
- timestamp (DATETIME)
- daily_change (REAL) - **True 24-hour change** (compares to rate from 24 hours ago)
- created_at (DATETIME)

### news
- id (INTEGER PRIMARY KEY)
- title (TEXT)
- description (TEXT)
- link (TEXT UNIQUE)
- source (TEXT)
- published_date (DATETIME)
- fetched_at (DATETIME)

### metadata
- metadata_key (TEXT PRIMARY KEY)
- metadata_value (TEXT)
- updated_at (DATETIME)

## Development

### Run Tests

```bash
pytest tests/ -v
```

### View Logs

```bash
tail -f logs/app.log
```

### Manual Database Query

```bash
sqlite3 data/financial_data.db
SELECT * FROM exchange_rates ORDER BY timestamp DESC LIMIT 10;
```

## Deployment

### Production Mode

Set environment variable:
```bash
export ENV=production
```

### Using gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.api.app:app
```

### Systemd Service

Create `/etc/systemd/system/financial-dashboard.service`:

```ini
[Unit]
Description=Financial Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/task5-mini-project
ExecStart=/usr/bin/python3 main.py schedule
Restart=always

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### No data showing
- Run `python main.py update` to collect initial data
- Check logs in `logs/app.log`
- Verify RSS feeds are accessible

### Database locked
- Close any other connections to the database
- Restart the application

### Port already in use
- Change `API_PORT` in `config.py`
- Or kill process using port 5000

## License

This project is part of the Python Extraction Tasks series.

## Author

Financial Dashboard Pipeline
Date: 2025-11-26
