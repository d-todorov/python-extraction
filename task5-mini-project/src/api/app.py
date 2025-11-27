"""
Flask REST API

Provides REST endpoints for financial dashboard.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import (
    DATABASE_PATH, API_HOST, API_PORT,
    MAX_HISTORY_DAYS, DEFAULT_HISTORY_DAYS,
    MAX_NEWS_LIMIT, DEFAULT_NEWS_LIMIT
)
from src.storage.database import Database

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')
CORS(app)

# Track app start time for uptime
app_start_time = datetime.now()


def get_db():
    """
    Get database connection for current request.
    
    Creates a new connection per request to avoid thread safety issues.
    """
    return Database(DATABASE_PATH)


@app.route('/')
def index():
    """Serve the dashboard UI."""
    return render_template('index.html')


@app.route('/api/rates', methods=['GET'])
def get_rates():
    """
    Get current exchange rates.
    
    Returns:
        JSON with current rates for all tracked currencies
    """
    db = None
    try:
        db = get_db()
        rates_data = db.get_latest_rates()
        
        if not rates_data:
            return jsonify({
                'error': 'No exchange rate data available'
            }), 404
        
        # Format response
        rates = {}
        timestamp = None
        
        for rate in rates_data:
            rates[rate['currency_code']] = rate['rate']
            if not timestamp:
                timestamp = rate['timestamp']
        
        response = {
            'base_currency': 'BGN',
            'timestamp': timestamp,
            'rates': rates
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting rates: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if db:
            db.close()


@app.route('/api/rates/history', methods=['GET'])
def get_rate_history():
    """
    Get historical exchange rates.
    
    Query Parameters:
        days (int): Number of days (default: 1, max: 7)
    
    Returns:
        JSON with historical rates for all currencies
    """
    db = None
    try:
        db = get_db()
        
        # Get and validate days parameter
        days = request.args.get('days', DEFAULT_HISTORY_DAYS, type=int)
        days = max(1, min(days, MAX_HISTORY_DAYS))  # Clamp to valid range
        
        history_data = db.get_rate_history(days)
        
        if not history_data:
            return jsonify({
                'error': 'No historical data available'
            }), 404
        
        # Group by date
        history_by_date = {}
        for record in history_data:
            date = record['date']
            currency = record['currency_code']
            
            if date not in history_by_date:
                history_by_date[date] = {}
            
            history_by_date[date][currency] = {
                'rate': record['rate'],
                'change': record['daily_change']
            }
        
        # Format response
        history = []
        for date in sorted(history_by_date.keys(), reverse=True):
            history.append({
                'date': date,
                'rates': history_by_date[date]
            })
        
        response = {
            'base_currency': 'BGN',
            'days': days,
            'history': history
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting rate history: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if db:
            db.close()


@app.route('/api/news', methods=['GET'])
def get_news():
    """
    Get recent financial news.
    
    Query Parameters:
        limit (int): Number of articles (default: 1, max: 10)
    
    Returns:
        JSON with recent news articles
    """
    db = None
    try:
        db = get_db()
        
        # Get and validate limit parameter
        limit = request.args.get('limit', DEFAULT_NEWS_LIMIT, type=int)
        limit = max(1, min(limit, MAX_NEWS_LIMIT))  # Clamp to valid range
        
        news_data = db.get_recent_news(limit)
        
        response = {
            'count': len(news_data),
            'news': news_data
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if db:
            db.close()


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Get system health status.
    
    Returns:
        JSON with system health information
    """
    db = None
    try:
        db = get_db()
        
        # Check database connection
        db_status = 'connected'
        try:
            db.connect()
        except:
            db_status = 'disconnected'
        
        # Get last update times
        last_rate_update = db.get_metadata('last_rate_update')
        last_news_update = db.get_metadata('last_news_update')
        
        # Calculate uptime
        uptime = (datetime.now() - app_start_time).total_seconds()
        
        response = {
            'status': 'healthy' if db_status == 'connected' else 'unhealthy',
            'database': db_status,
            'last_rate_update': last_rate_update,
            'last_news_update': last_news_update,
            'uptime_seconds': int(uptime)
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
    finally:
        if db:
            db.close()


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


def run_server():
    """Run the Flask development server."""
    logger.info(f"Starting API server on {API_HOST}:{API_PORT}")
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == '__main__':
    run_server()
