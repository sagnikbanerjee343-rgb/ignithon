# Traceable Impact Reporting for Small Nonprofits

A Streamlit and Pandas prototype that helps small nonprofits combine, clean, validate, and report program data from multiple file formats.

## Problem

Small nonprofits often store information in separate CSV, JSON, and Excel files. These files may contain duplicate beneficiaries, missing values, inconsistent column names, different date formats, and conflicting records.

This project creates a simple, source-traceable reporting workflow.

## Features

- Upload multiple CSV, JSON, and Excel files.
- Combine data from multiple sources.
- Standardize inconsistent column names.
- Clean whitespace and empty values.
- Convert dates to `YYYY-MM-DD`.
- Preserve original uploaded records.
- Remove duplicate `person_id` records from the cleaned view.
- Detect missing IDs, names, programs, outcomes, and dates.
- Detect duplicate beneficiaries.
- Detect conflicting program, outcome, location, and date values.
- Add source filename and source row information.
- Record transformation notes.
- Display summary metrics and limitations.
- Download cleaned records, summary reports, and issue reports.

## Technology

- Python
- Pandas
- Streamlit
- OpenPyXL
- RapidFuzz

No database is used. The prototype processes data in memory.

## Project Structure

```text
nonprofit-impact-tracker/
│
├── app.py
├── data_processing.py
├── metrics.py
├── requirements.txt
├── README.md
│
└── sample_data/
    ├── beneficiaries.csv
    ├── program_data.json
    └── outcomes.xlsx
```

## Installation

Install the required packages:

```bash
pip install -r requirements.txt
```

## Running the Application

Start the Streamlit application:

```bash
python -m streamlit run app.py
```

The application will open in a browser.

## How to Use

1. Start the application.
2. Upload one or more CSV, JSON, or Excel files.
3. Review the Summary Report.
4. Compare Original Records with Cleaned Records.
5. Review duplicate, missing-data, and conflict warnings.
6. Check the source file and source row for traceability.
7. Download the cleaned data or reports.

## Data Processing Workflow

```text
Uploaded Files
      ↓
File Reading
      ↓
Column Standardization
      ↓
Text and Date Cleaning
      ↓
Duplicate Detection
      ↓
Conflict Detection
      ↓
Duplicate Removal
      ↓
Metric Calculation
      ↓
Traceable Reports
```

## Standard Internal Columns

The application attempts to standardize uploaded files into these common fields:

```text
person_id
name
program
location
outcome
date
source_file
source_row
transformation_notes
```

Different input names are mapped automatically. For example:

```text
beneficiary_id → person_id
full_name → name
project_name → program
result → outcome
activity_date → date
```

## Duplicate Handling

Original records are never overwritten.

The application:

- Keeps every uploaded row in Original Records.
- Keeps the first valid occurrence of a `person_id`.
- Removes later repeated records from Cleaned Records.
- Displays removed duplicate rows in Data Quality.
- Keeps source filename and source row information for review.

Records without a reliable `person_id` are not automatically removed because they cannot be safely matched.

## Metric Definitions

### Unique Beneficiaries

The number of distinct, non-empty `person_id` values in the cleaned data.

### Active Programs

The number of distinct program names.

### Reported Positive Outcome Rate

The number of positive outcomes divided by the number of recorded outcomes.

This is a descriptive statistic and does not prove overall program impact.

### Duplicate Records

Repeated records with the same non-empty `person_id`.

### Conflicting Records

Records where the same person has different program, outcome, location, or date values across sources.

## Source Traceability

Each processed record retains:

```text
source_file
source_row
transformation_notes
```

This allows users to trace a cleaned value or reported issue back to its original source.

## Limitations

- This is a prototype and not a production data system.
- Data is processed in memory.
- Data is not permanently stored in a database.
- Duplicate matching is primarily based on person IDs and exact normalized names.
- Records without reliable IDs may remain unresolved.
- Uploaded files may not represent all nonprofit activities.
- Reported outcome rates do not establish causation or overall impact.
- The prototype uses synthetic or sample data and should not be used with sensitive personal information.

## Privacy

Do not upload real beneficiary information, phone numbers, email addresses, addresses, or other sensitive personal data.

Use synthetic or anonymized data for demonstrations.

## Future Improvements

- Add fuzzy matching for names.
- Add user-defined metric configuration.
- Add database storage.
- Add user authentication.
- Add PDF report generation.
- Add advanced data visualizations.
- Add review and approval workflows for duplicate removal.

## Project Objective

The objective of this prototype is to help small nonprofits create clearer, more trustworthy reports while showing how data was transformed and where each reported figure originated.
