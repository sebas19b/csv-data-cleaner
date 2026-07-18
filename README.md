#  Automated CSV Data Cleaner

Python script that automatically detects, cleans, and processes 
CSV files. Generates a full JSON report with all changes made.

## Features
- Removes duplicate and empty rows
- Validates and fixes email format
- Converts 8 different date formats to YYYY-MM-DD
- Fills missing numeric values with median/mean
- Normalizes text casing
- Generates detailed log and JSON report

## How to Run
1. Place your CSV files in the `input_csv/` folder
2. Run: `python csv_data_cleaner.py`
3. Find cleaned files in `output_clean/`

## Tools
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
