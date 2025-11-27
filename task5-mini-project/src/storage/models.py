"""
Data Models

Dataclasses representing database entities.

Author: Financial Dashboard Pipeline
Date: 2025-11-26
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExchangeRate:
    """Represents an exchange rate record."""
    currency_code: str
    rate: float
    base_currency: str = 'BGN'
    timestamp: Optional[datetime] = None
    daily_change: Optional[float] = None
    id: Optional[int] = None


@dataclass
class NewsItem:
    """Represents a news article."""
    title: str
    link: str
    source: str
    description: Optional[str] = None
    published_date: Optional[datetime] = None
    id: Optional[int] = None
