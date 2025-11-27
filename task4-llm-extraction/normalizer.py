"""
Data Normalization Utilities

Normalizes extracted financial data into standard formats.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import re
from datetime import datetime
from dateutil import parser
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def normalize_date(date_str: Any) -> Optional[str]:
    """
    Normalize date to ISO format (YYYY-MM-DD).
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        ISO formatted date string or None if invalid
    """
    if not date_str or date_str == "":
        return None
    
    # If already a string, try to parse
    if isinstance(date_str, str):
        try:
            # Remove common suffixes like "st", "nd", "rd", "th"
            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
            
            # Parse with dateutil (flexible parser)
            parsed_date = parser.parse(cleaned, dayfirst=False)
            
            # Return ISO format
            return parsed_date.strftime('%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            return None
    
    # If datetime object, convert directly
    if isinstance(date_str, datetime):
        return date_str.strftime('%Y-%m-%d')
    
    return None


def normalize_currency(currency: Any) -> Optional[str]:
    """
    Normalize currency to 3-letter ISO code.
    
    Args:
        currency: Currency symbol, code, or name
        
    Returns:
        3-letter ISO currency code or None
    """
    if not currency:
        return None
    
    currency_str = str(currency).strip().upper()
    
    # Direct mapping of symbols and names to codes
    currency_map = {
        '$': 'USD',
        'USD': 'USD',
        'DOLLAR': 'USD',
        'DOLLARS': 'USD',
        'US DOLLAR': 'USD',
        
        '€': 'EUR',
        'EUR': 'EUR',
        'EURO': 'EUR',
        'EUROS': 'EUR',
        
        '£': 'GBP',
        'GBP': 'GBP',
        'POUND': 'GBP',
        'POUNDS': 'GBP',
        'STERLING': 'GBP',
        
        'BGN': 'BGN',
        'ЛВ': 'BGN',
        'LEV': 'BGN',
        'LEVA': 'BGN',
        'BULGARIAN LEV': 'BGN',
        'BULGARIAN LEVA': 'BGN',
    }
    
    # Check direct match
    if currency_str in currency_map:
        return currency_map[currency_str]
    
    # Check if it's already a 3-letter code
    if len(currency_str) == 3 and currency_str.isalpha():
        return currency_str
    
    # Default to BGN if ambiguous
    logger.warning(f"Unknown currency '{currency}', defaulting to BGN")
    return 'BGN'


def normalize_amount(amount: Any) -> Optional[float]:
    """
    Normalize amount to clean float.
    
    Args:
        amount: Amount in various formats (string, number, with symbols)
        
    Returns:
        Clean float value or None if invalid
    """
    if amount is None or amount == "":
        return None
    
    # If already a number, return as float
    if isinstance(amount, (int, float)):
        return float(amount)
    
    # If string, clean and parse
    if isinstance(amount, str):
        try:
            # Remove currency symbols and whitespace
            cleaned = amount.strip()
            cleaned = re.sub(r'[€$£лв]', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            
            # Remove thousand separators (commas, spaces, periods in some locales)
            # Handle European format (1.234,56) vs US format (1,234.56)
            
            # Count periods and commas
            period_count = cleaned.count('.')
            comma_count = cleaned.count(',')
            
            if period_count > 1:
                # European format: 1.234.567,89
                cleaned = cleaned.replace('.', '')  # Remove thousand separators
                cleaned = cleaned.replace(',', '.')  # Convert decimal separator
            elif comma_count > 1:
                # US format with multiple commas: 1,234,567.89
                cleaned = cleaned.replace(',', '')  # Remove thousand separators
            elif period_count == 1 and comma_count == 1:
                # Determine which is decimal separator
                period_pos = cleaned.rfind('.')
                comma_pos = cleaned.rfind(',')
                if period_pos > comma_pos:
                    # US format: 1,234.56
                    cleaned = cleaned.replace(',', '')
                else:
                    # European format: 1.234,56
                    cleaned = cleaned.replace('.', '')
                    cleaned = cleaned.replace(',', '.')
            elif comma_count == 1 and period_count == 0:
                # Could be European decimal: 1234,56
                # Check if comma is in last 3 positions (likely decimal)
                if len(cleaned) - cleaned.rfind(',') <= 3:
                    cleaned = cleaned.replace(',', '.')
                else:
                    # Likely thousand separator
                    cleaned = cleaned.replace(',', '')
            
            # Remove any remaining non-numeric characters except decimal point and minus
            cleaned = re.sub(r'[^\d.-]', '', cleaned)
            
            # Convert to float
            value = float(cleaned)
            return value
            
        except Exception as e:
            logger.warning(f"Could not parse amount '{amount}': {e}")
            return None
    
    return None


def normalize_category(category: Any) -> Optional[str]:
    """
    Normalize category to standard format.
    
    Args:
        category: Category string
        
    Returns:
        Normalized category or None
    """
    if not category:
        return None
    
    category_str = str(category).strip().lower()
    
    # Map synonyms to standard categories
    expense_terms = ['expense', 'cost', 'expenditure', 'spending', 'outgoing']
    income_terms = ['income', 'revenue', 'earning', 'profit', 'receipt', 'incoming']
    
    for term in expense_terms:
        if term in category_str:
            return 'expense'
    
    for term in income_terms:
        if term in category_str:
            return 'income'
    
    # Return as-is if no match
    return category_str


def normalize_extraction(raw_data: Dict) -> Dict:
    """
    Apply all normalizations to extracted data.
    
    Args:
        raw_data: Raw extracted data dictionary
        
    Returns:
        Normalized data dictionary
    """
    normalized = {}
    
    # Normalize each field
    if 'company_name' in raw_data:
        # Keep company name as-is (proper noun)
        normalized['company_name'] = raw_data['company_name']
    
    if 'document_date' in raw_data:
        normalized['document_date'] = normalize_date(raw_data['document_date'])
    
    if 'total_amount' in raw_data:
        normalized['total_amount'] = normalize_amount(raw_data['total_amount'])
    
    if 'currency' in raw_data:
        normalized['currency'] = normalize_currency(raw_data['currency'])
    
    if 'category' in raw_data:
        normalized['category'] = normalize_category(raw_data['category'])
    
    # Pass through other fields as-is
    for key, value in raw_data.items():
        if key not in normalized:
            normalized[key] = value
    
    return normalized
