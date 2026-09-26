"""Small Pandas helpers for the nonprofit impact-reporting prototype."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


_COLUMN_ALIASES = {
    "id": "person_id",
    "beneficiary_id": "person_id",
    "person_id": "person_id",
    "beneficiary_name": "name",
    "full_name": "name",
    "name": "name",
    "project": "program",
    "project_name": "program",
    "program": "program",
    "result": "outcome",
    "status": "outcome",
    "outcome": "outcome",
    "date_of_activity": "date",
    "activity_date": "date",
    "date": "date",
    "participant_id": "person_id",
    "program_name": "program",
    "outcome_status": "outcome",
    "positive_outcome": "outcome",
}


def _uploaded_file_name(uploaded_file: Any) -> str:
    """Return a useful filename for Streamlit uploads and file-like objects."""

    name = getattr(uploaded_file, "name", None)
    return Path(str(name)).name if name else "uploaded_file"


def _read_from_start(uploaded_file: Any, reader: Any) -> pd.DataFrame:
    """Read an upload while supporting both Streamlit and normal file objects."""

    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    return reader(uploaded_file)


def read_uploaded_file(uploaded_file: Any) -> pd.DataFrame:
    """Read CSV, JSON, or Excel input and attach source-tracking columns.

    ``source_row`` is a one-based record number within the uploaded file. This
    convention also works for JSON, where a physical spreadsheet row does not
    exist.
    """

    if uploaded_file is None:
        raise ValueError("An uploaded file is required.")

    filename = _uploaded_file_name(uploaded_file)
    extension = Path(filename).suffix.lower()

    if extension == ".csv":
        dataframe = _read_from_start(uploaded_file, pd.read_csv)
    elif extension == ".json":
        dataframe = _read_from_start(uploaded_file, pd.read_json)
    elif extension in {".xlsx", ".xls"}:
        dataframe = _read_from_start(uploaded_file, pd.read_excel)
    else:
        raise ValueError(
            f"Unsupported file type '{extension or 'unknown'}'. "
            "Please upload a CSV, JSON, or Excel file."
        )

    # Remove genuinely blank input rows before adding metadata; otherwise the
    # metadata itself would make those rows appear non-empty.
    dataframe = dataframe.dropna(how="all").reset_index(drop=True)
    dataframe["source_file"] = filename
    dataframe["source_row"] = range(1, len(dataframe) + 1)
    return dataframe


def _normalise_column_name(column: Any) -> str:
    name = str(column).strip().lower()
    name = name.replace("-", "_").replace(" ", "_")
    while "__" in name:
        name = name.replace("__", "_")
    return name.strip("_")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names and map common input names to standard names."""

    result = df.copy()
    normalized_names = [_normalise_column_name(column) for column in result.columns]
    result.columns = [
        _COLUMN_ALIASES.get(name, name) for name in normalized_names
    ]

    # If a file contains both, for example, ``id`` and ``person_id``, the
    # aliases create duplicate column names. Merge them without discarding
    # non-empty values from either input column.
    duplicate_names = result.columns[result.columns.duplicated()].unique()
    for column in duplicate_names:
        duplicate_values = result.loc[:, result.columns == column]
        result = result.drop(columns=column)
        result[column] = duplicate_values.bfill(axis=1).iloc[:, 0]

    return result


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean simple text values while preserving questionable records."""

    result = df.copy()
    source_columns = {"source_file", "source_row"}
    data_columns = [column for column in result.columns if column not in source_columns]

    # Remove rows that contain no actual input data. Metadata columns are
    # intentionally excluded from this check.
    if data_columns:
        result = result.dropna(how="all", subset=data_columns)

    for column in result.select_dtypes(include=["object", "string"]).columns:
        values = result[column].astype("string").str.strip()
        values = values.replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "none": pd.NA,
                "null": pd.NA,
            }
        )
        result[column] = values

    return result.reset_index(drop=True)


def find_data_issues(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return row-level issues for missing IDs, outcomes, and programs."""

    issues: list[dict[str, Any]] = []
    checks = (
        ("person_id", "missing_person_id", "Missing person ID"),
        ("outcome", "missing_outcome", "Missing outcome"),
        ("program", "missing_program", "Missing program name"),
    )

    for index, row in df.iterrows():
        source_file = row.get("source_file", "unknown")
        source_row = row.get("source_row", index + 1)

        for column, issue_type, message in checks:
            if column in df.columns and not _is_empty(row.get(column)):
                continue

            issues.append(
                {
                    "type": issue_type,
                    "message": message,
                    "source_file": source_file,
                    "source_row": source_row,
                }
            )

    return issues

