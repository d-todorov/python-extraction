"""
Unit Tests for LLM Data Extraction

Tests for normalizer, validator, LLM extractor, and traditional extractor.

Author: LLM Data Extraction
Date: 2025-11-26
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from normalizer import (
    normalize_date, normalize_currency, normalize_amount,
    normalize_category, normalize_extraction
)
from validator import DataValidator, REQUIRED_FIELDS
from llm_extractor import LLMDataExtractor
from data_extractor import TraditionalExtractor


class TestNormalizer:
    """Test normalization functions."""
    
    def test_normalize_date_iso_format(self):
        """Test date already in ISO format."""
        assert normalize_date('2024-01-15') == '2024-01-15'
    
    def test_normalize_date_us_format(self):
        """Test US date format."""
        assert normalize_date('January 15, 2024') == '2024-01-15'
        assert normalize_date('01/15/2024') == '2024-01-15'
    
    def test_normalize_date_with_ordinals(self):
        """Test dates with ordinal suffixes."""
        assert normalize_date('January 15th, 2024') == '2024-01-15'
        assert normalize_date('March 3rd, 2024') == '2024-03-03'
    
    def test_normalize_date_invalid(self):
        """Test invalid date."""
        assert normalize_date('invalid') is None
        assert normalize_date('') is None
        assert normalize_date(None) is None
    
    def test_normalize_currency_symbols(self):
        """Test currency symbol normalization."""
        assert normalize_currency('$') == 'USD'
        assert normalize_currency('€') == 'EUR'
        assert normalize_currency('£') == 'GBP'
        assert normalize_currency('лв') == 'BGN'
    
    def test_normalize_currency_codes(self):
        """Test currency code normalization."""
        assert normalize_currency('USD') == 'USD'
        assert normalize_currency('eur') == 'EUR'
        assert normalize_currency('BGN') == 'BGN'
    
    def test_normalize_currency_names(self):
        """Test currency name normalization."""
        assert normalize_currency('dollar') == 'USD'
        assert normalize_currency('EURO') == 'EUR'
        assert normalize_currency('Bulgarian Lev') == 'BGN'
    
    def test_normalize_amount_clean_number(self):
        """Test clean number normalization."""
        assert normalize_amount(1234.56) == 1234.56
        assert normalize_amount('1234.56') == 1234.56
    
    def test_normalize_amount_with_commas(self):
        """Test US format with commas."""
        assert normalize_amount('1,234.56') == 1234.56
        assert normalize_amount('1,234,567.89') == 1234567.89
    
    def test_normalize_amount_european_format(self):
        """Test European format."""
        assert normalize_amount('1.234,56') == 1234.56
        assert normalize_amount('1.234.567,89') == 1234567.89
    
    def test_normalize_amount_with_currency_symbols(self):
        """Test amounts with currency symbols."""
        assert normalize_amount('$1,234.56') == 1234.56
        assert normalize_amount('€1.234,56') == 1234.56
    
    def test_normalize_amount_invalid(self):
        """Test invalid amounts."""
        assert normalize_amount('invalid') is None
        assert normalize_amount('') is None
        assert normalize_amount(None) is None
    
    def test_normalize_category(self):
        """Test category normalization."""
        assert normalize_category('expense') == 'expense'
        assert normalize_category('INCOME') == 'income'
        assert normalize_category('Revenue') == 'income'
        assert normalize_category('cost') == 'expense'
    
    def test_normalize_extraction_complete(self):
        """Test complete extraction normalization."""
        raw_data = {
            'company_name': 'Test Company',
            'document_date': 'January 15, 2024',
            'total_amount': '$1,234.56',
            'currency': '$',
            'category': 'EXPENSE'
        }
        
        normalized = normalize_extraction(raw_data)
        
        assert normalized['company_name'] == 'Test Company'
        assert normalized['document_date'] == '2024-01-15'
        assert normalized['total_amount'] == 1234.56
        assert normalized['currency'] == 'USD'
        assert normalized['category'] == 'expense'


class TestValidator:
    """Test validation functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
    
    def test_validate_amount_valid(self):
        """Test valid amount validation."""
        assert self.validator.validate_amount(100.50) is True
        assert self.validator.validate_amount(0) is True
        assert self.validator.validate_amount(1000000) is True
    
    def test_validate_amount_invalid(self):
        """Test invalid amount validation."""
        assert self.validator.validate_amount(-100) is False
        assert self.validator.validate_amount(None) is False
        assert self.validator.validate_amount('invalid') is False
    
    def test_validate_date_valid(self):
        """Test valid date validation."""
        assert self.validator.validate_date('2024-01-15') is True
        assert self.validator.validate_date('2023-12-31') is True
    
    def test_validate_date_invalid(self):
        """Test invalid date validation."""
        assert self.validator.validate_date('2024-13-01') is False  # Invalid month
        assert self.validator.validate_date('01/15/2024') is False  # Wrong format
        assert self.validator.validate_date('invalid') is False
        assert self.validator.validate_date(None) is False
    
    def test_validate_currency_valid(self):
        """Test valid currency validation."""
        assert self.validator.validate_currency('USD') is True
        assert self.validator.validate_currency('EUR') is True
        assert self.validator.validate_currency('BGN') is True
    
    def test_validate_currency_invalid(self):
        """Test invalid currency validation."""
        assert self.validator.validate_currency('US') is False  # Too short
        assert self.validator.validate_currency('USDD') is False  # Too long
        assert self.validator.validate_currency('$') is False
        assert self.validator.validate_currency(None) is False
    
    def test_validate_company_name_valid(self):
        """Test valid company name validation."""
        assert self.validator.validate_company_name('Acme Corp') is True
        assert self.validator.validate_company_name('Test Company Ltd.') is True
    
    def test_validate_company_name_invalid(self):
        """Test invalid company name validation."""
        assert self.validator.validate_company_name('A') is False  # Too short
        assert self.validator.validate_company_name('') is False
        assert self.validator.validate_company_name(None) is False
    
    def test_validate_required_fields(self):
        """Test required field validation."""
        complete_data = {
            'company_name': 'Test',
            'document_date': '2024-01-15',
            'total_amount': 100.0,
            'currency': 'USD'
        }
        assert self.validator.validate_required_fields(complete_data) == []
        
        incomplete_data = {'company_name': 'Test'}
        missing = self.validator.validate_required_fields(incomplete_data)
        assert 'document_date' in missing
        assert 'total_amount' in missing
        assert 'currency' in missing
    
    def test_validate_extraction_complete(self):
        """Test complete extraction validation."""
        valid_data = {
            'company_name': 'Test Company',
            'document_date': '2024-01-15',
            'total_amount': 1234.56,
            'currency': 'USD'
        }
        
        is_valid, errors = self.validator.validate_extraction(valid_data)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_extraction_with_errors(self):
        """Test extraction with validation errors."""
        invalid_data = {
            'company_name': '',  # Invalid
            'document_date': 'invalid',  # Invalid
            'total_amount': -100,  # Invalid
            'currency': '$'  # Invalid
        }
        
        is_valid, errors = self.validator.validate_extraction(invalid_data)
        assert is_valid is False
        assert len(errors) > 0


class TestLLMExtractor:
    """Test LLM extractor."""
    
    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        extractor = LLMDataExtractor(use_mock=True)
        assert extractor.use_mock is True
        assert extractor.client is None
    
    def test_extract_mock_invoice(self):
        """Test mock extraction from invoice."""
        extractor = LLMDataExtractor(use_mock=True)
        
        result = extractor.extract_from_document("INVOICE test", "invoice.txt")
        
        assert result['source_document'] == 'invoice.txt'
        assert result['extraction_method'] == 'mock'
        assert result['validation']['is_valid'] is True
        assert result['extracted_data']['company_name'] is not None
        assert result['extracted_data']['total_amount'] is not None
    
    def test_extract_mock_financial_table(self):
        """Test mock extraction from financial table."""
        extractor = LLMDataExtractor(use_mock=True)
        
        result = extractor.extract_from_document("QUARTERLY REPORT", "financial_table.txt")
        
        assert result['extraction_method'] == 'mock'
        assert result['validation']['is_valid'] is True
        assert result['extracted_data']['currency'] == 'EUR'
    
    def test_extract_mock_report(self):
        """Test mock extraction from report."""
        extractor = LLMDataExtractor(use_mock=True)
        
        result = extractor.extract_from_document("ANNUAL REPORT", "report_excerpt.txt")
        
        assert result['extraction_method'] == 'mock'
        assert result['validation']['is_valid'] is True
        assert result['extracted_data']['currency'] == 'BGN'
    
    def test_build_extraction_prompt(self):
        """Test prompt building."""
        extractor = LLMDataExtractor(use_mock=True)
        
        prompt = extractor._build_extraction_prompt("Test document")
        
        assert "Test document" in prompt
        assert "JSON" in prompt
        assert "company_name" in prompt
        assert "document_date" in prompt
    
    def test_parse_llm_response_valid_json(self):
        """Test parsing valid JSON response."""
        extractor = LLMDataExtractor(use_mock=True)
        
        response = '{"company_name": "Test", "total_amount": 100}'
        parsed = extractor._parse_llm_response(response)
        
        assert parsed['company_name'] == 'Test'
        assert parsed['total_amount'] == 100
    
    def test_parse_llm_response_with_extra_text(self):
        """Test parsing JSON with extra text."""
        extractor = LLMDataExtractor(use_mock=True)
        
        response = 'Here is the data: {"company_name": "Test"} as requested'
        parsed = extractor._parse_llm_response(response)
        
        assert parsed['company_name'] == 'Test'


class TestTraditionalExtractor:
    """Test traditional extractor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = TraditionalExtractor()
    
    def test_extract_company_name(self):
        """Test company name extraction."""
        text = "From: Acme Corporation Ltd.\nInvoice details..."
        name = self.extractor.extract_company_name(text)
        assert name == 'Acme Corporation Ltd.'
    
    def test_extract_date_various_formats(self):
        """Test date extraction from various formats."""
        text1 = "Date: January 15, 2024"
        assert self.extractor.extract_date(text1) == 'January 15, 2024'
        
        text2 = "Date: 01/15/2024"
        assert self.extractor.extract_date(text2) == '01/15/2024'
    
    def test_extract_amount(self):
        """Test amount extraction."""
        text = "TOTAL: $1,234.56"
        amount = self.extractor.extract_amount(text)
        assert amount is not None
    
    def test_extract_currency(self):
        """Test currency extraction."""
        text = "Total: $1,234.56 USD"
        currency = self.extractor.extract_currency(text)
        assert currency in ['$', 'USD']
    
    def test_extract_category(self):
        """Test category extraction."""
        invoice_text = "INVOICE #123\nPayment due..."
        assert self.extractor.extract_category(invoice_text) == 'expense'
        
        revenue_text = "Revenue Report\nTotal sales..."
        assert self.extractor.extract_category(revenue_text) == 'income'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
