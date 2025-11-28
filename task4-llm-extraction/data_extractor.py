"""
Traditional Data Extractor (Regex/Parsing-based)

Extracts financial data using traditional regex and string parsing methods.
This serves as a comparison baseline to the LLM approach.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import re
from typing import Dict, Optional, List
import logging

from normalizer import normalize_extraction
from validator import DataValidator

logger = logging.getLogger(__name__)


class TraditionalExtractor:
    """
    Extract financial data using regex and string parsing.
    
    This is a baseline comparison to the LLM approach.
    """
    
    def __init__(self):
        """Initialize the traditional extractor."""
        self.validator = DataValidator()
        logger.info("Initialized TraditionalExtractor")
    
    def extract_from_document(self, document_text: str, document_name: str = "document") -> Dict:
        """
        Extract data using traditional methods.
        
        Args:
            document_text: Raw document text
            document_name: Name of the document
            
        Returns:
            Dictionary with extracted data
        """
        logger.info(f"Extracting data (traditional) from: {document_name}")
        
        # Extract individual fields
        raw_extraction = {
            'company_name': self.extract_company_name(document_text),
            'document_date': self.extract_date(document_text),
            'total_amount': self.extract_amount(document_text),
            'currency': self.extract_currency(document_text),
            'category': self.extract_category(document_text),
            'line_items': None,  # Complex to extract with regex
            'additional_metrics': {}
        }
        
        # Normalize
        normalized_data = normalize_extraction(raw_extraction)
        
        # Validate
        is_valid, errors = self.validator.validate_extraction(normalized_data)
        
        # Build result
        result = {
            'source_document': document_name,
            'extraction_method': 'traditional',
            'model': 'regex',
            'extracted_data': normalized_data,
            'validation': {
                'is_valid': is_valid,
                'errors': errors
            }
        }
        
        if not is_valid:
            logger.warning(f"Validation errors for {document_name}: {errors}")
        
        return result
    
    def extract_company_name(self, text: str) -> Optional[str]:
        """
        Extract company name using patterns.
        
        Args:
            text: Document text
            
        Returns:
            Company name or None
        """
        # Pattern 1: "From: Company Name"
        pattern1 = r'From:\s*([^\n]+)'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: "Company: Company Name" or "Company Name:" at start of line
        pattern2 = r'^([A-Z][A-Za-z\s&.,]+(?:Ltd|Inc|Corp|JSC|LLC|GmbH)\.?)'
        match = re.search(pattern2, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # Pattern 3: Look for capitalized lines (likely company name)
        lines = text.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if len(line) > 5 and line[0].isupper() and any(term in line for term in ['Ltd', 'Inc', 'Corp', 'JSC', 'LLC']):
                return line
        
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """
        Extract date using regex patterns.
        
        Args:
            text: Document text
            
        Returns:
            Date string or None
        """
        # Pattern 1: "Date: MM/DD/YYYY" or "Date: Month DD, YYYY"
        pattern1 = r'Date:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: Standalone date formats
        # Month DD, YYYY
        pattern2 = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
        match = re.search(pattern2, text)
        if match:
            return match.group(0)
        
        # Pattern 3: DD/MM/YYYY or MM/DD/YYYY
        pattern3 = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'
        match = re.search(pattern3, text)
        if match:
            return match.group(0)
        
        # Pattern 4: YYYY-MM-DD
        pattern4 = r'\b\d{4}-\d{2}-\d{2}\b'
        match = re.search(pattern4, text)
        if match:
            return match.group(0)

        # Pattern 5: DD.MM.YYYY or MM.DD.YYYY
        pattern5 = r'\b\d{1,2}\.\d{1,2}\.\d{4}\b'
        match = re.search(pattern5, text)
        if match:
            return match.group(0)
        
        return None
    
    def extract_amount(self, text: str) -> Optional[float]:
        """
        Extract total amount using patterns.
        
        Args:
            text: Document text
            
        Returns:
            Amount as float or None
        """
        # Pattern 1: "TOTAL: $X,XXX.XX" or "Total: €X.XXX,XX"
        pattern1 = r'TOTAL[:\s]+[€$£лв]?\s*([\d,. ]+)'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).strip()
            # Let normalizer handle parsing
            return amount_str
        
        # Pattern 2: Look for largest amount in document
        # Find all amounts
        amounts = re.findall(r'[€$£]?\s*([\d,]+\.?\d*)', text)
        if amounts:
            # Convert to floats and find max
            try:
                parsed_amounts = []
                for amt in amounts:
                    cleaned = amt.replace(',', '').replace(' ', '')
                    if cleaned:
                        try:
                            parsed_amounts.append(float(cleaned))
                        except:
                            pass
                
                if parsed_amounts:
                    # Return the largest (likely the total)
                    return max(parsed_amounts)
            except:
                pass
        
        return None
    
    def extract_currency(self, text: str) -> Optional[str]:
        """
        Extract currency from document.
        
        Args:
            text: Document text
            
        Returns:
            Currency symbol/code or None
        """
        # Pattern 1: Explicit currency mention
        pattern1 = r'(?:Currency|amounts? in):\s*([A-Z]{3}|[$€£])'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern 2: Currency symbols in amounts
        symbols = re.findall(r'([$€£лв])\s*[\d,]+', text)
        if symbols:
            return symbols[0]
        
        # Pattern 3: Currency codes (USD, EUR, BGN, etc.)
        codes = re.findall(r'\b(USD|EUR|GBP|BGN|CHF)\b', text)
        if codes:
            return codes[0]
        
        return None
    
    def extract_category(self, text: str) -> Optional[str]:
        """
        Determine if document is expense or income.
        
        Args:
            text: Document text
            
        Returns:
            'expense' or 'income' or None
        """
        text_lower = text.lower()
        
        # Look for keywords
        expense_keywords = ['invoice', 'bill', 'expense', 'cost', 'payment due']
        income_keywords = ['revenue', 'income', 'sales', 'profit', 'receipt']
        
        expense_score = sum(1 for kw in expense_keywords if kw in text_lower)
        income_score = sum(1 for kw in income_keywords if kw in text_lower)
        
        if expense_score > income_score:
            return 'expense'
        elif income_score > expense_score:
            return 'income'
        
        return None
