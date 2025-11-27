"""
LLM Data Extractor

Extracts structured financial data from unstructured documents using OpenAI API.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import json
import logging
import os
from typing import Dict, Optional
from datetime import datetime

# OpenAI import with error handling
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI library not available. Only mock mode will work.")

from dotenv import load_dotenv
from normalizer import normalize_extraction
from validator import DataValidator

# Load environment variables
load_dotenv()

# Configure logging
# logging.basicConfig() is handled in main.py
logger = logging.getLogger(__name__)


class LLMDataExtractor:
    """
    Extract structured financial data using OpenAI's LLM.
    
    Features:
    - OpenAI API integration
    - Mock mode for testing without API
    - Automatic data normalization
    - Validation of extracted data
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = 'gpt-4o-mini', use_mock: bool = False):
        """
        Initialize the LLM data extractor.
        
        Args:
            api_key: OpenAI API key (if None, reads from environment)
            model: OpenAI model to use (default: gpt-4o-mini)
            use_mock: If True, use mock responses instead of API
        """
        self.model = model
        self.use_mock = use_mock or os.getenv('USE_MOCK', 'false').lower() == 'true'
        self.validator = DataValidator()
        
        # Initialize OpenAI client if not in mock mode
        if not self.use_mock:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not installed. Install with: pip install openai")
            
            self.api_key = api_key or os.getenv('OPENAI_API_KEY')
            if not self.api_key:
                raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
            
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"Initialized LLMDataExtractor with model: {self.model}")
        else:
            self.client = None
            logger.info("Initialized LLMDataExtractor in MOCK mode")
    
    def extract_from_document(self, document_text: str, document_name: str = "document") -> Dict:
        """
        Extract structured data from document text.
        
        Args:
            document_text: Raw document text
            document_name: Name of the document (for logging)
            
        Returns:
            Dictionary with extracted and normalized data
        """
        logger.info(f"Extracting data from: {document_name}")
        
        # Get raw extraction (from LLM or mock)
        if self.use_mock:
            raw_extraction = self._get_mock_response(document_text, document_name)
        else:
            raw_extraction = self._extract_with_llm(document_text)
        
        # Normalize the extracted data
        normalized_data = normalize_extraction(raw_extraction)
        
        # Validate the normalized data
        is_valid, errors = self.validator.validate_extraction(normalized_data)
        
        # Build result
        result = {
            'source_document': document_name,
            'extraction_method': 'mock' if self.use_mock else 'llm',
            'model': 'mock' if self.use_mock else self.model,
            'extracted_data': normalized_data,
            'validation': {
                'is_valid': is_valid,
                'errors': errors
            },
            'extracted_at': datetime.now().isoformat()
        }
        
        if not is_valid:
            logger.warning(f"Validation errors for {document_name}: {errors}")
        else:
            logger.info(f"Successfully extracted and validated data from {document_name}")
        
        return result
    
    def _build_extraction_prompt(self, document_text: str) -> str:
        """
        Build the prompt for LLM extraction.
        
        Args:
            document_text: Document text to extract from
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a financial data extraction expert. Extract structured information from the following document.

DOCUMENT:
{document_text}

INSTRUCTIONS:
Extract the following information and return it as a JSON object:
- company_name: The name of the company (from invoice, report, etc.)
- document_date: The date of the document (not today's date)
- total_amount: The main total amount (as a number, without currency symbols)
- currency: The currency code or symbol used
- category: Whether this is an "expense" or "income" document
- line_items: If applicable, list of individual items with descriptions and amounts
- additional_metrics: Any other relevant financial metrics (revenue, profit, expenses, etc.)

IMPORTANT:
- Return ONLY valid JSON, no additional text
- Use null for missing values
- Extract amounts as numbers without currency symbols
- Be precise with the document date (not the current date)
- For reports with multiple amounts, extract all relevant metrics in additional_metrics

JSON OUTPUT:"""
        
        return prompt
    
    def _extract_with_llm(self, document_text: str) -> Dict:
        """
        Extract data using OpenAI API.
        
        Args:
            document_text: Document text to extract from
            
        Returns:
            Raw extracted data dictionary
        """
        try:
            # Build prompt
            prompt = self._build_extraction_prompt(document_text)
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial data extraction expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1000
            )
            
            # Extract response text
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            extracted_data = self._parse_llm_response(response_text)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """
        Parse LLM JSON response.
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Parsed dictionary
        """
        try:
            # Try to find JSON in response (in case LLM added extra text)
            # Look for content between first { and last }
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_str = response_text[start:end]
                data = json.loads(json_str)
                return data
            else:
                # Try parsing the whole response
                data = json.loads(response_text)
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            raise ValueError(f"LLM did not return valid JSON: {e}")
    
    def _get_mock_response(self, document_text: str, document_name: str) -> Dict:
        """
        Get mock response for testing without API.
        
        Args:
            document_text: Document text (used to determine which mock to return)
            document_name: Document name
            
        Returns:
            Mock extracted data
        """
        logger.info(f"Using mock response for: {document_name}")
        
        # Determine which document based on content or name
        if 'invoice' in document_name.lower() or 'INVOICE' in document_text:
            return {
                'company_name': 'Acme Corporation Ltd.',
                'document_date': 'January 15, 2024',
                'total_amount': '7,692.00',
                'currency': '$',
                'category': 'expense',
                'line_items': [
                    {'description': 'Software Development Services', 'amount': 3400.00},
                    {'description': 'Cloud Infrastructure Setup', 'amount': 1250.00},
                    {'description': 'Technical Consulting', 'amount': 960.00},
                    {'description': 'Database Migration Services', 'amount': 800.00}
                ],
                'additional_metrics': {
                    'subtotal': 6410.00,
                    'tax': 1282.00,
                    'tax_rate': 0.20
                }
            }
        
        elif 'financial_table' in document_name.lower() or 'QUARTERLY' in document_text:
            return {
                'company_name': 'TechStart Industries Inc.',
                'document_date': 'December 31, 2023',
                'total_amount': '369501.25',
                'currency': 'EUR',
                'category': 'income',
                'line_items': [
                    {'description': 'Product Sales', 'amount': 245680.50},
                    {'description': 'Service Revenue', 'amount': 89320.75},
                    {'description': 'Licensing Fees', 'amount': 34500.00}
                ],
                'additional_metrics': {
                    'total_revenue': 369501.25,
                    'total_expenses': 311951.25,
                    'net_profit': 57550.00,
                    'quarter': 'Q4 2023'
                }
            }
        
        elif 'report' in document_name.lower() or 'ANNUAL REPORT' in document_text:
            return {
                'company_name': 'Bulgarian Energy Solutions JSC',
                'document_date': 'March 31, 2024',
                'total_amount': '12500000',
                'currency': 'BGN',
                'category': 'income',
                'line_items': None,
                'additional_metrics': {
                    'total_revenue': 12500000,
                    'operating_expenses': 8300000,
                    'personnel_costs': 4200000,
                    'capital_expenditures': 2100000,
                    'net_income': 3100000,
                    'gross_profit_margin': 0.336,
                    'net_profit_margin': 0.248,
                    'total_assets': 45800000,
                    'total_liabilities': 22400000,
                    'shareholders_equity': 23400000,
                    'cash_flow_operations': 5700000
                }
            }
        
        else:
            # Generic mock response
            return {
                'company_name': 'Unknown Company',
                'document_date': '2024-01-01',
                'total_amount': '1000.00',
                'currency': 'USD',
                'category': 'expense',
                'line_items': None,
                'additional_metrics': {}
            }
