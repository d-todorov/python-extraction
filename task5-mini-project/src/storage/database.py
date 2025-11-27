"""
Database Layer

SQLite database connection and operations.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database wrapper for financial dashboard.
    
    Provides connection management and CRUD operations.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> sqlite3.Connection:
        """
        Create database connection.
        
        Returns:
            SQLite connection object
        """
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Enable column access by name
        return self.conn
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """Create database tables if they don't exist."""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Exchange rates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency_code TEXT NOT NULL,
                rate REAL NOT NULL,
                base_currency TEXT DEFAULT 'BGN',
                timestamp DATETIME NOT NULL,
                daily_change REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(currency_code, timestamp)
            )
        ''')
        
        # News table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                link TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                published_date DATETIME,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                metadata_key TEXT PRIMARY KEY,
                metadata_value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    def execute(self, query: str, params: tuple = ()) -> int:
        """
        Execute a query that modifies data (INSERT, UPDATE, DELETE).
        
        Args:
            query: SQL query with ? placeholders
            params: Values to substitute for placeholders
            
        Returns:
            Number of affected rows
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """
        Execute a SELECT query and return one row.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            Dict with column names as keys, or None if no results
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Execute a SELECT query and return all rows.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            List of dicts, or empty list if no results
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    # Exchange Rate Operations
    
    def insert_exchange_rate(self, currency_code: str, rate: float, timestamp: datetime, 
                            daily_change: Optional[float] = None, base_currency: str = 'BGN'):
        """Insert exchange rate record."""
        query = '''
            INSERT OR REPLACE INTO exchange_rates 
            (currency_code, rate, base_currency, timestamp, daily_change)
            VALUES (?, ?, ?, ?, ?)
        '''
        self.execute(query, (currency_code, rate, base_currency, timestamp, daily_change))
        logger.debug(f"Inserted rate: {currency_code} = {rate}")
    
    def get_latest_rates(self) -> List[Dict]:
        """Get most recent exchange rates for all currencies."""
        query = '''
            SELECT currency_code, rate, daily_change, timestamp
            FROM exchange_rates
            WHERE timestamp = (
                SELECT MAX(timestamp) FROM exchange_rates
            )
            ORDER BY currency_code
        '''
        return self.fetch_all(query)
    
    def get_rate_history(self, days: int = 7) -> List[Dict]:
        """
        Get historical exchange rates.
        
        Args:
            days: Number of days of history
            
        Returns:
            List of rate records
        """
        query = '''
            SELECT currency_code, rate, daily_change, 
                   DATE(timestamp) as date
            FROM exchange_rates
            WHERE timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC, currency_code
        '''
        return self.fetch_all(query, (days,))
    
    def get_previous_rate(self, currency_code: str) -> Optional[float]:
        """
        Get the rate from 24 hours ago for calculating true daily change.
        
        Args:
            currency_code: Currency code
            
        Returns:
            Rate from 24 hours ago, or None if not available
        """
        query = '''
            SELECT rate FROM exchange_rates
            WHERE currency_code = ?
            AND timestamp <= datetime('now', '-24 hours')
            ORDER BY timestamp DESC
            LIMIT 1
        '''
        result = self.fetch_one(query, (currency_code,))
        return result['rate'] if result else None
    
    # News Operations
    
    def insert_news(self, title: str, link: str, source: str, 
                   description: Optional[str] = None, 
                   published_date: Optional[datetime] = None):
        """Insert news article (ignores duplicates)."""
        query = '''
            INSERT OR IGNORE INTO news 
            (title, description, link, source, published_date)
            VALUES (?, ?, ?, ?, ?)
        '''
        rows_affected = self.execute(query, (title, description, link, source, published_date))
        if rows_affected > 0:
            logger.debug(f"Inserted news: {title[:50]}...")
        return rows_affected
    
    def get_recent_news(self, limit: int = 10) -> List[Dict]:
        """
        Get recent news articles.
        
        Args:
            limit: Maximum number of articles
            
        Returns:
            List of news articles
        """
        query = '''
            SELECT id, title, description, link, source, published_date
            FROM news
            ORDER BY published_date DESC, fetched_at DESC
            LIMIT ?
        '''
        return self.fetch_all(query, (limit,))
    
    # Metadata Operations
    
    def update_metadata(self, key: str, value: str):
        """Update metadata key-value pair."""
        query = '''
            INSERT OR REPLACE INTO metadata (metadata_key, metadata_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        '''
        self.execute(query, (key, value))
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        result = self.fetch_one('SELECT metadata_value FROM metadata WHERE metadata_key = ?', (key,))
        return result['metadata_value'] if result else None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
