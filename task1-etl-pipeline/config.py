"""
Configuration for ETL Pipeline

Author: ETL Pipeline
Date: 2025-11-27
"""

# Currency conversion rates to BGN
# Note: These rates should be updated regularly or fetched from an API
CURRENCY_RATES = {
    'EUR': 1.96,
    'USD': 1.80,
    'GBP': 2.30,
    'BGN': 1.00
}

# Required columns in input CSV
REQUIRED_COLUMNS = ['date', 'revenue', 'expenses', 'currency', 'category']

# Input/Output file paths
DEFAULT_INPUT_FILE = 'dirty_financial_data.csv'
DEFAULT_OUTPUT_FILE = 'output_clean_data.json'
DEFAULT_REPORT_FILE = 'data_quality_report.txt'

# Data quality settings
MAX_SAMPLE_CORRECTIONS = 10  # Number of corrections to show in report
DECIMAL_PLACES = 2  # Decimal places for monetary amounts
