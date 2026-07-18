
# PROYECT: Automated CSV Data Cleaner & Processor
# Autor: Sebastian B. | Systems Engineer & AI Data Specialist
# Description: A script that automatically detects, cleans, and processes
#              CSV files, generating a final report.


import os
import csv
import json
import logging
import re
from pathlib import Path
from datetime import datetime



# SETTINGS


INPUT_FOLDER  = "input_csv"     # Folder where the raw CSV files are read
OUTPUT_FOLDER = "output_clean"  # folder where the cleaned CSV files are stored
LOG_FILE      = "cleaner.log"   # log file

# Expected columns (automatically adjusts if some are missing)
EXPECTED_COLUMNS = ["id", "name", "email", "age", "country", "salary", "date"]

# Configurable Cleaning Rules
RULES = {
    "remove_duplicates":    True,
    "strip_whitespace":     True,
    "fix_email_format":     True,
    "fill_missing_numeric": "median",   # 'median', 'mean', 'zero' o None
    "standardize_dates":    True,       # convert date to YYYY-MM-DD
    "remove_empty_rows":    True,
    "normalize_text_case":  "title",    # 'title', 'upper', 'lower' o None
}



# LOGGING


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)



#PROFITS


def ensure_folders():
    """Create the input and output folders if they do not exist."""
    Path(INPUT_FOLDER).mkdir(exist_ok=True)
    Path(OUTPUT_FOLDER).mkdir(exist_ok=True)


def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w{2,}$'
    return bool(re.match(pattern, email.strip()))


def parse_date(value: str) -> str:
    """Try converting different date formats to YYYY-MM-DD."""
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y",
        "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d",
        "%d %b %Y", "%B %d, %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value  # If it could not be converted, return the original


def compute_median(values: list) -> float:
    nums = sorted(v for v in values if v is not None)
    if not nums:
        return 0.0
    mid = len(nums) // 2
    return (nums[mid] + nums[~mid]) / 2


def compute_mean(values: list) -> float:
    nums = [v for v in values if v is not None]
    return sum(nums) / len(nums) if nums else 0.0



# CLAENING ROWS


def clean_row(row: dict, numeric_fills: dict) -> tuple:
    """
    Cleans an individual row by applying all configured rules.
    Returns (cleaned_row, list_of_found_issues).
    """
    issues = []
    cleaned = {}

    for col, val in row.items():
        val = str(val) if val is not None else ""

        # 1. Remove extra space
        if RULES["strip_whitespace"]:
            val = val.strip()

        # 2. Normalie text
        if RULES["normalize_text_case"] and col in ("name", "country"):
            if val:
                if RULES["normalize_text_case"] == "title":
                    val = val.title()
                elif RULES["normalize_text_case"] == "upper":
                    val = val.upper()
                elif RULES["normalize_text_case"] == "lower":
                    val = val.lower()

        # 3. Validate and flag invalid emails
        if col == "email" and val:
            if RULES["fix_email_format"] and not is_valid_email(val):
                issues.append(f"Invalid email: '{val}'")
                val = val.lower().replace(" ", "")  # intento básico de corrección

        # 4. Standardize dates
        if col == "date" and val and RULES["standardize_dates"]:
            converted = parse_date(val)
            if converted != val:
                issues.append(f"Date converted: '{val}' → '{converted}'")
            val = converted

        # 5. Handle empty numeric values
        if col in ("age", "salary") and val == "":
            fill = numeric_fills.get(col, 0)
            issues.append(f"Missing {col} filled with {fill}")
            val = str(round(fill, 2))

        cleaned[col] = val

    return cleaned, issues



# PROCESAMIENTO DE UN ARCHIVO CSV


def process_csv(filepath: str) -> dict:
    """
    Reads, cleans, and saves a CSV file.
    Returns a dictionary with the report of that file.
    """
    filename  = Path(filepath).name
    log.info(f"Processing: {filename}")

    report = {
        "file":             filename,
        "total_rows":       0,
        "cleaned_rows":     0,
        "duplicates_removed": 0,
        "empty_rows_removed": 0,
        "issues_found":     [],
        "output_file":      ""
    }

    # --- READ CSV ---
    rows = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for row in reader:
            rows.append(dict(row))

    report["total_rows"] = len(rows)
    log.info(f"  Rows read: {len(rows)} | Columns: {headers}")

    # --- Remove completely empty rows ---
    if RULES["remove_empty_rows"]:
        before = len(rows)
        rows = [r for r in rows if any(v.strip() for v in r.values())]
        removed = before - len(rows)
        report["empty_rows_removed"] = removed
        if removed:
            log.info(f"  Empty rows removed: {removed}")

    # --- Calculate Numerical Interpolation Values ---
    numeric_fills = {}
    if RULES["fill_missing_numeric"]:
        for col in ("age", "salary"):
            if col in (headers or []):
                vals = []
                for r in rows:
                    try:
                        vals.append(float(r.get(col, "")))
                    except (ValueError, TypeError):
                        pass
                if RULES["fill_missing_numeric"] == "median":
                    numeric_fills[col] = compute_median(vals)
                elif RULES["fill_missing_numeric"] == "mean":
                    numeric_fills[col] = compute_mean(vals)
                else:
                    numeric_fills[col] = 0.0

    # --- Clean rows ---
    cleaned_rows = []
    all_issues   = []
    for i, row in enumerate(rows, start=1):
        cleaned, issues = clean_row(row, numeric_fills)
        cleaned_rows.append(cleaned)
        for issue in issues:
            all_issues.append({"row": i, "issue": issue})

    report["issues_found"] = all_issues

    # --- Remove duplicates ---
    if RULES["remove_duplicates"]:
        before = len(cleaned_rows)
        seen   = set()
        unique = []
        for r in cleaned_rows:
            key = tuple(r.values())
            if key not in seen:
                seen.add(key)
                unique.append(r)
        cleaned_rows = unique
        report["duplicates_removed"] = before - len(cleaned_rows)
        if report["duplicates_removed"]:
            log.info(f"  Duplicates removed: {report['duplicates_removed']}")

    report["cleaned_rows"] = len(cleaned_rows)

    # --- Save cleaned CSV ---
    out_name = f"clean_{filename}"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)
    if cleaned_rows:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=cleaned_rows[0].keys())
            writer.writeheader()
            writer.writerows(cleaned_rows)
        report["output_file"] = out_path
        log.info(f"  Saved: {out_path} ({len(cleaned_rows)} rows)")
    else:
        log.warning(f"  No rows remaining after cleaning: {filename}")

    return report



# GENERATE FINAL REPORT

def generate_report(reports: list):
    """Generates a JSON summary and a console summary."""
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(OUTPUT_FOLDER, f"report_{timestamp}.json")

    summary = {
        "generated_at":   datetime.now().isoformat(),
        "files_processed": len(reports),
        "total_rows_in":  sum(r["total_rows"]  for r in reports),
        "total_rows_out": sum(r["cleaned_rows"] for r in reports),
        "total_duplicates_removed": sum(r["duplicates_removed"] for r in reports),
        "total_empty_removed":      sum(r["empty_rows_removed"] for r in reports),
        "total_issues_found":       sum(len(r["issues_found"])  for r in reports),
        "files": reports
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    log.info("\n" + "="*55)
    log.info("  CLEANING SUMMARY")
    log.info("="*55)
    log.info(f"  Files processed    : {summary['files_processed']}")
    log.info(f"  Rows in            : {summary['total_rows_in']}")
    log.info(f"  Rows out (clean)   : {summary['total_rows_out']}")
    log.info(f"  Duplicates removed : {summary['total_duplicates_removed']}")
    log.info(f"  Empty rows removed : {summary['total_empty_removed']}")
    log.info(f"  Issues detected    : {summary['total_issues_found']}")
    log.info(f"  Report saved to    : {report_path}")
    log.info("="*55)

    return summary


# DEMO SCRIPT: Generates sample “dirty” CSV files


def create_sample_dirty_csvs():
    """Generates sample “dirty” CSV files for demonstration."""
    Path(INPUT_FOLDER).mkdir(exist_ok=True)

    # CSV 1: Data of employees with various issues
    employees = [
        ["id","name","email","age","country","salary","date"],
        ["1","  alice johnson  ","alice@email.com","28","usa","55000","2024-01-15"],
        ["2","CARLOS RUIZ","carlos@email","35","mexico","","15/03/2023"],
        ["3","Emma Wilson","emma@email.com","","UK","72000","03/25/2024"],
        ["4","david kim","david@email.com","29","south korea","61000","2024-04-05"],
        ["5","Sofia Martinez","sofia @email.com","31","colombia","48000","18-06-2023"],
        ["2","CARLOS RUIZ","carlos@email","35","mexico","","15/03/2023"],  # duplicado
        ["6","","","","","",""],                                            # fila vacía
        ["7","James Brown","james@email.com","45","USA","93000","November 30, 2021"],
        ["8","  laura perez","laura@email.com","22","colombia","38000","2024-01-02"],
    ]

    # CSV 2: Data of customers with mixed dates
    customers = [
        ["id","name","email","age","country","salary","date"],
        ["101","Michael Scott","michael@company.com","50","USA","120000","May 14, 2021"],
        ["102","priya sharma","priya@company.com","33","india","67000","19/08/2023"],
        ["103","YUKI TANAKA","yuki@company","27","japan","","25 Sep 2022"],
        ["104","laura castro","laura2@company.com","21","colombia","29000","2024-03-22"],
        ["105","Daniel Flores","daniel@company.com","","mexico","54000","08/01/2020"],
        ["105","Daniel Flores","daniel@company.com","","mexico","54000","08/01/2020"], # duplicado
        ["106","Mia Johnson","mia@@company.com","23","USA","47000","2021-12-01"],
    ]

    with open(f"{INPUT_FOLDER}/employees_dirty.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(employees)

    with open(f"{INPUT_FOLDER}/customers_dirty.csv", "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(customers)

    log.info("Sample dirty CSV files created in 'input_csv/' folder.")



# MAIN


def main():
    log.info("CSV Data Cleaner started.")
    ensure_folders()

    # Generate sample CSVs if the folder is empty
    input_files = list(Path(INPUT_FOLDER).glob("*.csv"))
    if not input_files:
        log.info("No CSV files found. Creating sample dirty files...")
        create_sample_dirty_csvs()
        input_files = list(Path(INPUT_FOLDER).glob("*.csv"))

    # Process each file
    reports = []
    for csv_file in input_files:
        try:
            report = process_csv(str(csv_file))
            reports.append(report)
        except Exception as e:
            log.error(f"Error processing {csv_file.name}: {e}")

    # Generate final report
    if reports:
        generate_report(reports)
    else:
        log.warning("No files were processed.")

    log.info("Done.")


if __name__ == "__main__":
    main()