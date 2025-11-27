"""
Data Validation Utilities

Validates extracted and normalized financial data.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import re
from datetime import datetime
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

# Required fields for a valid extraction
REQUIRED_FIELDS = ['company_name', 'document_date', 'total_amount', 'currency']

# Valid currency codes (ISO 4217 - common ones)
VALID_CURRENCIES = {
    'USD', 'EUR', 'GBP', 'BGN', 'CHF', 'JPY', 'CNY', 'AUD', 'CAD', 'NZD',
    'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'RUB', 'TRY', 'INR'
}


class DataValidator:
    """Validator for extracted financial data."""
    
    def validate_extraction(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate complete extraction.
        
        Args:
            data: Extracted data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        missing_fields = self.validate_required_fields(data)
        if missing_fields:
            errors.extend([f"Missing required field: {field}" for field in missing_fields])
        
        # Validate individual fields if present
        if 'total_amount' in data:
            if not self.validate_amount(data['total_amount']):
                errors.append(f"Invalid amount: {data['total_amount']}")
        
        if 'document_date' in data:
            if not self.validate_date(data['document_date']):
                errors.append(f"Invalid date: {data['document_date']}")
        
        if 'currency' in data:
            if not self.validate_currency(data['currency']):
                errors.append(f"Invalid currency: {data['currency']}")
        
        if 'company_name' in data:
            if not self.validate_company_name(data['company_name']):
                errors.append(f"Invalid company name: {data['company_name']}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_amount(self, amount: Any) -> bool:
        """
        Validate that amount is a valid number.
        
        Args:
            amount: Amount to validate
            
        Returns:
            True if valid, False otherwise
        """
        if amount is None:
            return False
        
        try:
            # Convert to float
            value = float(amount)
            
            # Check if positive (totals should be positive)
            if value < 0:
                logger.warning(f"Amount is negative: {value}")
                return False
            
            # Check if reasonable (not too large)
            if value > 1e12:  # 1 trillion
                logger.warning(f"Amount seems unreasonably large: {value}")
                return False
            
            return True
        except (ValueError, TypeError):
            return False
    
    def validate_date(self, date_str: Any) -> bool:
        """
        Validate that date is in proper format.
        
        Args:
            date_str: Date string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not date_str:
            return False
        
        # Check if it's ISO format (YYYY-MM-DD)
        iso_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(iso_pattern, str(date_str)):
            logger.warning(f"Date not in ISO format: {date_str}")
            return False
        
        # Try to parse to ensure it's a valid date
        try:
            datetime.strptime(str(date_str), '%Y-%m-%d')
            
            # Check if date is not in the future (financial docs shouldn't be future-dated)
            date_obj = datetime.strptime(str(date_str), '%Y-%m-%d')
            if date_obj > datetime.now():
                logger.warning(f"Date is in the future: {date_str}")
                # Don't fail validation, just warn
            
            return True
        except ValueError:
            return False
    
    def validate_currency(self, currency: Any) -> bool:
        """
        Validate that currency is a valid ISO code.
        
        Args:
            currency: Currency code to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not currency:
            return False
        
        currency_str = str(currency).strip().upper()
        
        # Check if it's a 3-letter code
        if len(currency_str) != 3:
            return False
        
        # Check if it's in our list of valid currencies
        if currency_str not in VALID_CURRENCIES:
            logger.warning(f"Currency code not in common list: {currency_str}")
            # Don't fail - might be a valid but uncommon currency
            # Just check if it's 3 letters
            return currency_str.isalpha()
        
        return True
    
    def validate_company_name(self, company_name: Any) -> bool:
        """
        Validate company name.
        
        Args:
            company_name: Company name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not company_name:
            return False
        
        name_str = str(company_name).strip()
        
        # Check if not empty
        if len(name_str) == 0:
            return False
        
        # Check if reasonable length (not too short, not too long)
        if len(name_str) < 2:
            logger.warning(f"Company name seems too short: {name_str}")
            return False
        
        if len(name_str) > 200:
            logger.warning(f"Company name seems too long: {name_str}")
            return False
        
        return True
    
    def validate_required_fields(self, data: Dict) -> List[str]:
        """
        Check for missing required fields.
        
        Args:
            data: Data dictionary to check
            
        Returns:
            List of missing field names
        """
        missing = []
        
        for field in REQUIRED_FIELDS:
            if field not in data or data[field] is None or data[field] == "":
                missing.append(field)
        
        return missing
