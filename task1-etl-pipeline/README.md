# Task 1: ETL Pipeline

Clean and transform messy financial data using pandas.

## Features

- ✅ Date parsing (multiple formats)
- ✅ Currency standardization
- ✅ Amount cleaning (removes $, commas)
- ✅ Category classification
- ✅ Data validation
- ✅ Quality tracking

## Quick Start

```bash
cd task1-etl-pipeline
pip install -r requirements.txt
python etl_pipeline.py
```

## Input/Output

**Input**: `dirty_financial_data.csv` - Messy financial data with inconsistent formats

**Output**: 
- `output_clean_data.json` - Cleaned and normalized data
- `data_quality_report.txt` - Quality metrics and statistics

## Example Transformation

**Before**:
```
date: 12/15/2023.
amount: $1,234.56
category: Office Supplies
```

**After**:
```json
{
  "date": "2023-12-15",
  "amount": 1234.56,
  "category": "office_supplies"
}
```

## Data Quality Report

The pipeline generates a report showing:
- Total records processed
- Records cleaned vs. failed
- Specific transformations applied
- Data quality metrics

## Technologies

- **pandas** - Data manipulation
- **python-dateutil** - Flexible date parsing

## Author

ETL Pipeline Task  
Date: 2025-11-26
