"""
ETL Pipeline for Financial Data Cleaning

This script extracts financial data from a CSV file, transforms it by cleaning
and standardizing the data, and loads it into JSON format with a quality report.

Author: ETL Pipeline
Date: 2025-11-25
"""

import pandas as pd
import logging
import json
import sys
from datetime import datetime
from dateutil import parser
from typing import Dict, List, Tuple
import re
import config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Import currency rates from config
CURRENCY_RATES = config.CURRENCY_RATES


class DataQualityTracker:
    """Tracks data quality issues during ETL process."""
    
    def __init__(self):
        self.total_records = 0
        self.removed_records = []
        self.cleaned_records = []
        self.duplicates_removed = 0
    
    def add_removed(self, index: int, reason: str):
        """Record a removed record with reason."""
        self.removed_records.append({'index': index, 'reason': reason})
    
    def add_cleaned(self, index: int, field: str, old_value: str, new_value: str):
        """Record a cleaned field."""
        self.cleaned_records.append({
            'index': index,
            'field': field,
            'old_value': str(old_value),
            'new_value': str(new_value)
        })


def extract_data(file_path: str) -> Tuple[pd.DataFrame, DataQualityTracker]:
    """
    Extract data from CSV file with column validation.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        Tuple of (DataFrame, DataQualityTracker)
        
    Raises:
        ValueError: If required columns are missing
    """
    logger.info(f"Starting data extraction from {file_path}")
    tracker = DataQualityTracker()
    
    try:
        # Read CSV with minimal parsing to preserve original data
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        tracker.total_records = len(df)
        logger.info(f"Successfully loaded {len(df)} records")
        
        # Validate required columns exist
        missing_columns = set(config.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            error_msg = f"Missing required columns: {', '.join(missing_columns)}"
            logger.error(error_msg)
            logger.error(f"Available columns: {', '.join(df.columns)}")
            raise ValueError(error_msg)
        
        logger.info("Column validation passed")
        return df, tracker
        
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        raise


def clean_dates(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Clean and standardize date formats.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with cleaned dates
    """
    logger.info("Cleaning date fields")
    
    def parse_date(date_str: str, index: int) -> str:
        """Parse date string to ISO format."""
        if not date_str or date_str.strip() == '':
            return None
        
        try:
            # Remove trailing periods
            date_str = date_str.strip().rstrip('.')
            
            # Try parsing with dateutil (assumes M/D/Y for ambiguous dates)
            parsed_date = parser.parse(date_str, dayfirst=False)
            iso_date = parsed_date.strftime('%Y-%m-%d')
            
            if date_str != iso_date:
                tracker.add_cleaned(index, 'date', date_str, iso_date)
            
            return iso_date
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}' at index {index}: {e}")
            return None
    
    df['date'] = df.apply(lambda row: parse_date(row['date'], row.name), axis=1)
    return df


def clean_numeric_field(value: str, index: int, field: str, tracker: DataQualityTracker) -> float:
    """
    Clean and validate numeric fields.
    
    Args:
        value: String value to clean
        index: Row index
        field: Field name
        tracker: Data quality tracker
        
    Returns:
        Cleaned numeric value or None
    """
    if not value or value.strip() == '' or value.upper() == 'N/A':
        return None
    
    try:
        # Remove extra periods (e.g., "312.927.93" -> "312927.93")
        # Keep only the last period as decimal separator
        original_value = value
        parts = value.split('.')
        if len(parts) > 2:
            # Multiple periods - join all but last, then add last with period
            value = ''.join(parts[:-1]) + '.' + parts[-1]
            tracker.add_cleaned(index, field, original_value, value)
        
        numeric_value = float(value)
        
        # Take absolute value of negative expenses (data entry errors)
        if field == 'expenses' and numeric_value < 0:
            tracker.add_cleaned(index, field, str(numeric_value), str(abs(numeric_value)))
            numeric_value = abs(numeric_value)
        
        return numeric_value
    except ValueError:
        logger.warning(f"Could not parse numeric value '{value}' for {field} at index {index}")
        return None


def clean_numeric_fields(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Clean revenue and expenses fields.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with cleaned numeric fields
    """
    logger.info("Cleaning numeric fields")
    
    df['revenue'] = df.apply(
        lambda row: clean_numeric_field(row['revenue'], row.name, 'revenue', tracker),
        axis=1
    )
    df['expenses'] = df.apply(
        lambda row: clean_numeric_field(row['expenses'], row.name, 'expenses', tracker),
        axis=1
    )
    
    return df


def clean_categories(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Clean category field by fixing typos.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with cleaned categories
    """
    logger.info("Cleaning category field")
    
    def fix_category(category: str, index: int) -> str:
        """Fix common typos in category names."""
        if not category:
            return category
        
        original = category

        # Known categories
        valid_categories = ['Marketing', 'Operations', 'Sales', 'R&D']

        # Fix typos like "?arketing" -> "Marketing", "?perations" -> "Operations"
        if category not in valid_categories:
            # Remove leading special characters for matching
            cleaned = category.lstrip('?!@#$%^*()').strip()
            
            # Find the best match (case-insensitive)
            best_match = None
            for valid_cat in valid_categories:
                # Check if cleaned is a substring of valid_cat OR valid_cat starts with cleaned
                if (cleaned.lower() in valid_cat.lower() or 
                    valid_cat.lower().startswith(cleaned.lower())):
                    best_match = valid_cat
                    break
            
            # If no match found, just capitalize the cleaned version
            category = best_match if best_match else cleaned.capitalize()
            tracker.add_cleaned(index, 'category', original, category)
        
        return category
    
    df['category'] = df.apply(lambda row: fix_category(row['category'], row.name), axis=1)
    return df


def remove_invalid_records(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Remove records with missing critical fields.
    
    Records are invalid if they are missing:
    - Date
    - Revenue
    - Expenses
    - Currency
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with invalid records removed
    """
    logger.info("Removing invalid records")
    
    initial_count = len(df)
    
    # Track which records to remove
    to_remove = []
    
    for idx, row in df.iterrows():
        reasons = []
        
        if pd.isna(row['date']) or row['date'] is None:
            reasons.append('missing date')
        
        if pd.isna(row['revenue']) or row['revenue'] is None:
            reasons.append('missing revenue')
        
        if pd.isna(row['expenses']) or row['expenses'] is None:
            reasons.append('missing expenses')
        
        if not row['currency'] or row['currency'].strip() == '':
            reasons.append('missing currency')
        
        if reasons:
            reason = ', '.join(reasons)
            tracker.add_removed(idx, reason)
            to_remove.append(idx)
    
    # Remove invalid records
    df = df.drop(to_remove)
    df = df.reset_index(drop=True)
    
    removed_count = initial_count - len(df)
    logger.info(f"Removed {removed_count} invalid records")
    
    return df


def remove_duplicates(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Remove duplicate records, keeping the first occurrence.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with duplicates removed
    """
    logger.info("Removing duplicate records")
    
    initial_count = len(df)
    
    # Find duplicates
    duplicates = df.duplicated(keep='first')
    duplicate_indices = df[duplicates].index.tolist()
    
    for idx in duplicate_indices:
        tracker.add_removed(idx, 'duplicate record')
    
    # Remove duplicates
    df = df.drop_duplicates(keep='first')
    df = df.reset_index(drop=True)
    
    tracker.duplicates_removed = initial_count - len(df)
    logger.info(f"Removed {tracker.duplicates_removed} duplicate records")
    
    return df


def convert_currency_to_bgn(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Convert all monetary amounts to BGN.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        DataFrame with amounts converted to BGN
    """
    logger.info("Converting currencies to BGN")
    
    def convert_amount(amount: float, currency: str) -> float:
        """Convert amount to BGN using fixed rates."""
        if pd.isna(amount) or not currency:
            return None
        
        rate = CURRENCY_RATES.get(currency.upper(), 1.0)
        return round(amount * rate, 2)
    
    # Store original currency
    df['original_currency'] = df['currency']
    
    # Convert amounts
    df['revenue_bgn'] = df.apply(
        lambda row: convert_amount(row['revenue'], row['currency']),
        axis=1
    )
    df['expenses_bgn'] = df.apply(
        lambda row: convert_amount(row['expenses'], row['currency']),
        axis=1
    )
    
    logger.info("Currency conversion completed")
    return df


def calculate_profit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate profit as revenue minus expenses.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with profit column added
    """
    logger.info("Calculating profit")
    
    df['profit_bgn'] = df.apply(
        lambda row: round(row['revenue_bgn'] - row['expenses_bgn'], 2)
        if pd.notna(row['revenue_bgn']) and pd.notna(row['expenses_bgn'])
        else None,
        axis=1
    )
    
    return df


def transform_data(df: pd.DataFrame, tracker: DataQualityTracker) -> pd.DataFrame:
    """
    Apply all transformation steps to the data.
    
    Args:
        df: Input DataFrame
        tracker: Data quality tracker
        
    Returns:
        Transformed DataFrame
    """
    logger.info("Starting data transformation")
    
    # Clean dates
    df = clean_dates(df, tracker)
    
    # Clean numeric fields
    df = clean_numeric_fields(df, tracker)
    
    # Clean categories
    df = clean_categories(df, tracker)
    
    # Remove invalid records
    df = remove_invalid_records(df, tracker)
    
    # Remove duplicates
    df = remove_duplicates(df, tracker)
    
    # Convert currency to BGN
    df = convert_currency_to_bgn(df, tracker)
    
    # Calculate profit
    df = calculate_profit(df)
    
    logger.info("Data transformation completed")
    return df


def save_to_json(df: pd.DataFrame, output_file: str):
    """
    Save cleaned data to JSON file.
    
    Args:
        df: Cleaned DataFrame
        output_file: Path to output JSON file
    """
    logger.info(f"Saving cleaned data to {output_file}")
    
    # Select and rename columns for output
    output_df = df[[
        'date', 'company_id', 'revenue_bgn', 'expenses_bgn',
        'profit_bgn', 'original_currency', 'category'
    ]].copy()
    
    # Convert to JSON
    output_data = output_df.to_dict(orient='records')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Successfully saved {len(output_data)} records to JSON")


def generate_quality_report(tracker: DataQualityTracker, final_count: int, output_file: str):
    """
    Generate data quality report.
    
    Args:
        tracker: Data quality tracker
        final_count: Final number of records
        output_file: Path to output report file
    """
    logger.info(f"Generating data quality report to {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("DATA QUALITY REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Summary statistics
        f.write("SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total records processed:     {tracker.total_records}\n")
        f.write(f"Records removed:             {len(tracker.removed_records)}\n")
        f.write(f"Records cleaned/corrected:   {len(tracker.cleaned_records)}\n")
        f.write(f"Duplicate records removed:   {tracker.duplicates_removed}\n")
        f.write(f"Final valid records:         {final_count}\n")
        f.write(f"Data quality rate:           {(final_count / tracker.total_records * 100):.2f}%\n\n")
        
        # Removed records breakdown
        if tracker.removed_records:
            f.write("REMOVED RECORDS\n")
            f.write("-" * 80 + "\n")
            
            # Group by reason
            reason_counts = {}
            for record in tracker.removed_records:
                reason = record['reason']
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {reason}: {count} records\n")
            f.write("\n")
        
        # Cleaned records breakdown
        if tracker.cleaned_records:
            f.write("CLEANED/CORRECTED RECORDS\n")
            f.write("-" * 80 + "\n")
            
            # Group by field
            field_counts = {}
            for record in tracker.cleaned_records:
                field = record['field']
                field_counts[field] = field_counts.get(field, 0) + 1
            
            for field, count in sorted(field_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {field}: {count} corrections\n")
            f.write("\n")
            
            # Show sample corrections
            f.write("Sample Corrections:\n")
            for record in tracker.cleaned_records[:10]:  # Show first 10
                f.write(f"  Row {record['index']} - {record['field']}: "
                       f"'{record['old_value']}' -> '{record['new_value']}'\n")
            if len(tracker.cleaned_records) > 10:
                f.write(f"  ... and {len(tracker.cleaned_records) - 10} more\n")
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")
    
    logger.info("Data quality report generated successfully")


def main():
    """Main ETL pipeline execution."""
    try:
        logger.info("=" * 80)
        logger.info("ETL Pipeline Started")
        logger.info("=" * 80)
        
        # Extract
        df, tracker = extract_data('dirty_financial_data.csv')
        
        # Transform
        df_clean = transform_data(df, tracker)
        
        # Load
        save_to_json(df_clean, 'output_clean_data.json')
        generate_quality_report(tracker, len(df_clean), 'data_quality_report.txt')
        
        logger.info("=" * 80)
        logger.info("ETL Pipeline Completed Successfully")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"ETL Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
