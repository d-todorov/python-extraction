"""
Unit Tests for ETL Pipeline

Tests all core functions of the ETL pipeline including extraction,
transformation, and loading operations.

Author: ETL Pipeline Tests
Date: 2025-11-25
"""

import pytest
import pandas as pd
import json
import os
from datetime import datetime
from etl_pipeline import (
    extract_data,
    clean_dates,
    clean_numeric_field,
    clean_numeric_fields,
    clean_categories,
    remove_invalid_records,
    remove_duplicates,
    convert_currency_to_bgn,
    calculate_profit,
    save_to_json,
    generate_quality_report,
    DataQualityTracker,
    CURRENCY_RATES
)


@pytest.fixture
def sample_data():
    """Create sample DataFrame for testing."""
    data = {
        'date': ['1/15/2024', '28/5/2024', '', '3/20/2024', '3/20/2024'],
        'company_id': ['COMP001', 'COMP002', 'COMP003', 'COMP004', 'COMP004'],
        'revenue': ['100000', '200.000.50', 'N/A', '150000', '150000'],
        'expenses': ['50000', '100000', '75000', '-5000', '-5000'],
        'currency': ['USD', 'EUR', '', 'GBP', 'GBP'],
        'category': ['Sales', 'Operations', '?arketing', 'R&D', 'R&D']
    }
    return pd.DataFrame(data)


@pytest.fixture
def tracker():
    """Create DataQualityTracker instance."""
    return DataQualityTracker()


class TestDataQualityTracker:
    """Test DataQualityTracker class."""
    
    def test_initialization(self):
        """Test tracker initialization."""
        tracker = DataQualityTracker()
        assert tracker.total_records == 0
        assert len(tracker.removed_records) == 0
        assert len(tracker.cleaned_records) == 0
        assert tracker.duplicates_removed == 0
    
    def test_add_removed(self, tracker):
        """Test adding removed records."""
        tracker.add_removed(5, 'missing date')
        assert len(tracker.removed_records) == 1
        assert tracker.removed_records[0]['index'] == 5
        assert tracker.removed_records[0]['reason'] == 'missing date'
    
    def test_add_cleaned(self, tracker):
        """Test adding cleaned records."""
        tracker.add_cleaned(3, 'date', '28/5/2024', '2024-05-28')
        assert len(tracker.cleaned_records) == 1
        assert tracker.cleaned_records[0]['field'] == 'date'
        assert tracker.cleaned_records[0]['old_value'] == '28/5/2024'
        assert tracker.cleaned_records[0]['new_value'] == '2024-05-28'


class TestExtraction:
    """Test data extraction functions."""
    
    def test_extract_data_success(self, tmp_path):
        """Test successful data extraction."""
        # Create temporary CSV file
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("date,company_id,revenue,expenses,currency,category\n"
                           "1/15/2024,COMP001,100000,50000,USD,Sales\n")
        
        df, tracker = extract_data(str(csv_file))
        assert len(df) == 1
        assert tracker.total_records == 1
        assert 'date' in df.columns
    
    def test_extract_data_file_not_found(self):
        """Test extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_data('nonexistent.csv')
    
    def test_extract_data_missing_required_columns(self, tmp_path):
        """Test extraction fails when required columns are missing."""
        # Create CSV with missing 'revenue' and 'expenses' columns
        csv_file = tmp_path / "test_missing_cols.csv"
        csv_file.write_text("date,company_id,currency,category\n"
                           "1/15/2024,COMP001,USD,Sales\n")
        
        with pytest.raises(ValueError) as exc_info:
            extract_data(str(csv_file))
        
        # Verify error message mentions missing columns
        error_msg = str(exc_info.value)
        assert "Missing required columns" in error_msg
        assert "revenue" in error_msg or "expenses" in error_msg
    
    def test_extract_data_missing_single_column(self, tmp_path):
        """Test extraction fails when a single required column is missing."""
        # Create CSV missing only 'currency' column
        csv_file = tmp_path / "test_missing_currency.csv"
        csv_file.write_text("date,company_id,revenue,expenses,category\n"
                           "1/15/2024,COMP001,100000,50000,Sales\n")
        
        with pytest.raises(ValueError) as exc_info:
            extract_data(str(csv_file))
        
        error_msg = str(exc_info.value)
        assert "Missing required columns" in error_msg
        assert "currency" in error_msg
    
    def test_extract_data_all_required_columns_present(self, tmp_path):
        """Test extraction succeeds when all required columns are present."""
        # Create CSV with all required columns
        csv_file = tmp_path / "test_all_cols.csv"
        csv_file.write_text("date,company_id,revenue,expenses,currency,category\n"
                           "1/15/2024,COMP001,100000,50000,USD,Sales\n")
        
        # Should not raise any exception
        df, tracker = extract_data(str(csv_file))
        assert len(df) == 1
        assert tracker.total_records == 1
    
    def test_extract_data_extra_columns_allowed(self, tmp_path):
        """Test extraction succeeds with extra columns beyond required ones."""
        # Create CSV with extra columns
        csv_file = tmp_path / "test_extra_cols.csv"
        csv_file.write_text("date,company_id,revenue,expenses,currency,category,extra_col1,extra_col2\n"
                           "1/15/2024,COMP001,100000,50000,USD,Sales,value1,value2\n")
        
        # Should not raise any exception
        df, tracker = extract_data(str(csv_file))
        assert len(df) == 1
        assert 'extra_col1' in df.columns
        assert 'extra_col2' in df.columns


class TestDateCleaning:
    """Test date cleaning functions."""
    
    def test_clean_dates_valid(self, sample_data, tracker):
        """Test cleaning valid dates."""
        df = clean_dates(sample_data.copy(), tracker)
        assert df.loc[0, 'date'] == '2024-01-15'
        assert df.loc[3, 'date'] == '2024-03-20'
    
    def test_clean_dates_invalid_format(self, sample_data, tracker):
        """Test cleaning dates with invalid format (day > 12)."""
        df = clean_dates(sample_data.copy(), tracker)
        # "28/5/2024" should be parsed as May 28, 2024
        assert df.loc[1, 'date'] == '2024-05-28'
    
    def test_clean_dates_missing(self, sample_data, tracker):
        """Test handling missing dates."""
        df = clean_dates(sample_data.copy(), tracker)
        assert pd.isna(df.loc[2, 'date']) or df.loc[2, 'date'] is None


class TestNumericCleaning:
    """Test numeric field cleaning functions."""
    
    def test_clean_numeric_field_valid(self, tracker):
        """Test cleaning valid numeric value."""
        result = clean_numeric_field('100000', 0, 'revenue', tracker)
        assert result == 100000.0
    
    def test_clean_numeric_field_malformed(self, tracker):
        """Test cleaning malformed number with multiple periods."""
        result = clean_numeric_field('200.000.50', 0, 'revenue', tracker)
        assert result == 200000.50
        assert len(tracker.cleaned_records) == 1
    
    def test_clean_numeric_field_na(self, tracker):
        """Test handling N/A values."""
        result = clean_numeric_field('N/A', 0, 'revenue', tracker)
        assert result is None
    
    def test_clean_numeric_field_empty(self, tracker):
        """Test handling empty values."""
        result = clean_numeric_field('', 0, 'revenue', tracker)
        assert result is None
    
    def test_clean_numeric_field_negative_expense(self, tracker):
        """Test converting negative expenses to absolute value."""
        result = clean_numeric_field('-5000', 0, 'expenses', tracker)
        assert result == 5000.0
        assert len(tracker.cleaned_records) == 1
    
    def test_clean_numeric_fields_dataframe(self, sample_data, tracker):
        """Test cleaning numeric fields in DataFrame."""
        df = clean_numeric_fields(sample_data.copy(), tracker)
        assert df.loc[0, 'revenue'] == 100000.0
        assert df.loc[1, 'revenue'] == 200000.50
        assert pd.isna(df.loc[2, 'revenue'])
        # Negative expense should be converted to positive
        assert df.loc[3, 'expenses'] == 5000.0


class TestCategoryCleaning:
    """Test category cleaning functions."""
    
    def test_clean_categories_typo(self, sample_data, tracker):
        """Test fixing category typos."""
        df = clean_categories(sample_data.copy(), tracker)
        # "?arketing" should become "Marketing"
        assert df.loc[2, 'category'] == 'Marketing'
        assert len(tracker.cleaned_records) == 1
    
    def test_clean_categories_valid(self, sample_data, tracker):
        """Test that valid categories are unchanged."""
        df = clean_categories(sample_data.copy(), tracker)
        assert df.loc[0, 'category'] == 'Sales'
        assert df.loc[1, 'category'] == 'Operations'


class TestInvalidRecordRemoval:
    """Test invalid record removal."""
    
    def test_remove_invalid_missing_currency(self, sample_data, tracker):
        """Test removing records with missing currency."""
        # First clean the data
        df = sample_data.copy()
        df = clean_dates(df, tracker)
        df = clean_numeric_fields(df, tracker)
        
        initial_count = len(df)
        df = remove_invalid_records(df, tracker)
        
        # Row 2 has missing currency, should be removed
        assert len(df) < initial_count
    
    def test_remove_invalid_missing_date(self, tracker):
        """Test removing records with missing date."""
        data = {
            'date': [None, '2024-01-15'],
            'company_id': ['COMP001', 'COMP002'],
            'revenue': [100000.0, 200000.0],
            'expenses': [50000.0, 100000.0],
            'currency': ['USD', 'EUR'],
            'category': ['Sales', 'Operations']
        }
        df = pd.DataFrame(data)
        
        df = remove_invalid_records(df, tracker)
        assert len(df) == 1
        assert df.loc[0, 'company_id'] == 'COMP002'


class TestDuplicateRemoval:
    """Test duplicate record removal."""
    
    def test_remove_duplicates(self, sample_data, tracker):
        """Test removing duplicate records."""
        # Rows 3 and 4 are duplicates
        df = remove_duplicates(sample_data.copy(), tracker)
        
        # Should have one less record
        assert len(df) == 4
        assert tracker.duplicates_removed == 1
    
    def test_remove_duplicates_none(self, tracker):
        """Test with no duplicates."""
        data = {
            'date': ['2024-01-15', '2024-01-16'],
            'company_id': ['COMP001', 'COMP002'],
            'revenue': ['100000', '200000'],
            'expenses': ['50000', '100000'],
            'currency': ['USD', 'EUR'],
            'category': ['Sales', 'Operations']
        }
        df = pd.DataFrame(data)
        
        df = remove_duplicates(df, tracker)
        assert len(df) == 2
        assert tracker.duplicates_removed == 0


class TestCurrencyConversion:
    """Test currency conversion functions."""
    
    def test_convert_currency_usd_to_bgn(self, tracker):
        """Test USD to BGN conversion."""
        data = {
            'date': ['2024-01-15'],
            'company_id': ['COMP001'],
            'revenue': [100000.0],
            'expenses': [50000.0],
            'currency': ['USD'],
            'category': ['Sales']
        }
        df = pd.DataFrame(data)
        
        df = convert_currency_to_bgn(df, tracker)
        
        # USD rate is 1.80
        assert df.loc[0, 'revenue_bgn'] == 180000.0
        assert df.loc[0, 'expenses_bgn'] == 90000.0
        assert df.loc[0, 'original_currency'] == 'USD'
    
    def test_convert_currency_eur_to_bgn(self, tracker):
        """Test EUR to BGN conversion."""
        data = {
            'date': ['2024-01-15'],
            'company_id': ['COMP001'],
            'revenue': [100000.0],
            'expenses': [50000.0],
            'currency': ['EUR'],
            'category': ['Sales']
        }
        df = pd.DataFrame(data)
        
        df = convert_currency_to_bgn(df, tracker)
        
        # EUR rate is 1.96
        assert df.loc[0, 'revenue_bgn'] == 196000.0
        assert df.loc[0, 'expenses_bgn'] == 98000.0
    
    def test_convert_currency_gbp_to_bgn(self, tracker):
        """Test GBP to BGN conversion."""
        data = {
            'date': ['2024-01-15'],
            'company_id': ['COMP001'],
            'revenue': [100000.0],
            'expenses': [50000.0],
            'currency': ['GBP'],
            'category': ['Sales']
        }
        df = pd.DataFrame(data)
        
        df = convert_currency_to_bgn(df, tracker)
        
        # GBP rate is 2.30
        assert df.loc[0, 'revenue_bgn'] == 230000.0
        assert df.loc[0, 'expenses_bgn'] == 115000.0
    
    def test_convert_currency_bgn_to_bgn(self, tracker):
        """Test BGN to BGN conversion (no change)."""
        data = {
            'date': ['2024-01-15'],
            'company_id': ['COMP001'],
            'revenue': [100000.0],
            'expenses': [50000.0],
            'currency': ['BGN'],
            'category': ['Sales']
        }
        df = pd.DataFrame(data)
        
        df = convert_currency_to_bgn(df, tracker)
        
        # BGN rate is 1.00
        assert df.loc[0, 'revenue_bgn'] == 100000.0
        assert df.loc[0, 'expenses_bgn'] == 50000.0


class TestProfitCalculation:
    """Test profit calculation."""
    
    def test_calculate_profit(self):
        """Test profit calculation."""
        data = {
            'revenue_bgn': [180000.0, 200000.0],
            'expenses_bgn': [90000.0, 150000.0]
        }
        df = pd.DataFrame(data)
        
        df = calculate_profit(df)
        
        assert df.loc[0, 'profit_bgn'] == 90000.0
        assert df.loc[1, 'profit_bgn'] == 50000.0
    
    def test_calculate_profit_negative(self):
        """Test profit calculation with loss."""
        data = {
            'revenue_bgn': [100000.0],
            'expenses_bgn': [150000.0]
        }
        df = pd.DataFrame(data)
        
        df = calculate_profit(df)
        
        assert df.loc[0, 'profit_bgn'] == -50000.0


class TestLoading:
    """Test data loading functions."""
    
    def test_save_to_json(self, tmp_path):
        """Test saving data to JSON."""
        data = {
            'date': ['2024-01-15'],
            'company_id': ['COMP001'],
            'revenue_bgn': [180000.0],
            'expenses_bgn': [90000.0],
            'profit_bgn': [90000.0],
            'original_currency': ['USD'],
            'category': ['Sales']
        }
        df = pd.DataFrame(data)
        
        output_file = tmp_path / "output.json"
        save_to_json(df, str(output_file))
        
        # Verify file exists and contains correct data
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            loaded_data = json.load(f)
        
        assert len(loaded_data) == 1
        assert loaded_data[0]['company_id'] == 'COMP001'
        assert loaded_data[0]['revenue_bgn'] == 180000.0
    
    def test_generate_quality_report(self, tmp_path, tracker):
        """Test generating quality report."""
        tracker.total_records = 100
        tracker.add_removed(5, 'missing date')
        tracker.add_removed(10, 'missing currency')
        tracker.add_cleaned(15, 'date', '28/5/2024', '2024-05-28')
        tracker.duplicates_removed = 3
        
        output_file = tmp_path / "report.txt"
        generate_quality_report(tracker, 95, str(output_file))
        
        # Verify file exists and contains expected content
        assert output_file.exists()
        
        content = output_file.read_text()
        assert 'DATA QUALITY REPORT' in content
        assert 'Total records processed:     100' in content
        assert 'Final valid records:         95' in content
        assert 'Duplicate records removed:   3' in content


class TestEndToEnd:
    """Test end-to-end pipeline."""
    
    def test_full_pipeline(self, tmp_path):
        """Test complete ETL pipeline."""
        # Create test CSV
        csv_content = """date,company_id,revenue,expenses,currency,category
1/15/2024,COMP001,100000,50000,USD,Sales
28/5/2024,COMP002,200.000.50,100000,EUR,Operations
,COMP003,150000,75000,GBP,?arketing
3/20/2024,COMP004,N/A,80000,BGN,R&D
3/20/2024,COMP004,N/A,80000,BGN,R&D"""
        
        csv_file = tmp_path / "test_data.csv"
        csv_file.write_text(csv_content)
        
        # Run extraction
        df, tracker = extract_data(str(csv_file))
        assert len(df) == 5
        
        # Run transformation
        df = clean_dates(df, tracker)
        df = clean_numeric_fields(df, tracker)
        df = clean_categories(df, tracker)
        df = remove_invalid_records(df, tracker)
        df = remove_duplicates(df, tracker)
        df = convert_currency_to_bgn(df, tracker)
        df = calculate_profit(df)
        
        # Verify results
        assert len(df) >= 1  # At least one valid record
        assert 'profit_bgn' in df.columns
        assert 'revenue_bgn' in df.columns
        assert 'expenses_bgn' in df.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
