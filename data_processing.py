from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


_COLUMN_ALIASES = {
    "id": "person_id",
    "participant_id": "person_id",
    "beneficiary_id": "person_id",
    "person_id": "person_id",
    "beneficiary_name": "name",
    "participant_name": "name",
    "full_name": "name",
    "name": "name",
    "project": "program",
    "project_name": "program",
    "program_name": "program",
    "program": "program",
    "result": "outcome",
    "status": "outcome",
    "outcome_status": "outcome",
    "positive_outcome": "outcome",
    "outcome": "outcome",
    "date_of_activity": "date",
    "activity_date": "date",
    "event_date": "date",
    "date": "date",
}


def _is_empty(value: Any) -> bool:
    if value is None:
        return True

    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def _get_filename(uploaded_file: Any) -> str:
    filename = getattr(uploaded_file, "name", None)

    if filename:
        return Path(str(filename)).name

    return "uploaded_file"


def _read_from_start(uploaded_file: Any, reader: Any) -> pd.DataFrame:
    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    return reader(uploaded_file)


def read_uploaded_file(uploaded_file: Any) -> pd.DataFrame:
    """Read CSV, JSON, or Excel files with source tracking."""

    if uploaded_file is None:
        raise ValueError("No file was provided.")

    filename = _get_filename(uploaded_file)
    extension = Path(filename).suffix.lower()

    if extension == ".csv":
        dataframe = _read_from_start(uploaded_file, pd.read_csv)

    elif extension == ".json":
        dataframe = _read_from_start(uploaded_file, pd.read_json)

    elif extension in {".xlsx", ".xls"}:
        dataframe = _read_from_start(uploaded_file, pd.read_excel)

    else:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            "Please upload CSV, JSON, or Excel files."
        )

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
    """Standardize column names and record the transformation."""

    result = df.copy()

    original_columns = list(result.columns)

    standardized_columns = [
        _COLUMN_ALIASES.get(
            _normalise_column_name(column),
            _normalise_column_name(column),
        )
        for column in original_columns
    ]

    result.columns = standardized_columns

    changes = []

    for original, standardized in zip(
        original_columns,
        standardized_columns,
    ):
        if str(original) != standardized:
            changes.append(
                f"{original} -> {standardized}"
            )

    duplicate_names = (
        result.columns[result.columns.duplicated()]
        .unique()
    )

    for column in duplicate_names:
        duplicate_values = result.loc[
            :,
            result.columns == column,
        ]

        merged_values = (
            duplicate_values
            .bfill(axis=1)
            .iloc[:, 0]
        )

        result = result.drop(columns=column)
        result[column] = merged_values

    if "transformation_notes" not in result.columns:
        result["transformation_notes"] = ""

    if changes:
        note = "Columns standardized: " + "; ".join(changes)

        result["transformation_notes"] = (
            result["transformation_notes"]
            .fillna("")
            .astype(str)
            .apply(
                lambda existing: (
                    f"{existing}; {note}"
                    if existing.strip()
                    else note
                )
            )
        )

    return result


def _append_note(
    dataframe: pd.DataFrame,
    mask: pd.Series,
    note: str,
) -> None:
    mask = mask.reindex(
        dataframe.index,
        fill_value=False,
    ).fillna(False)

    for index in dataframe.index[mask]:
        existing = dataframe.at[
            index,
            "transformation_notes",
        ]

        if _is_empty(existing):
            dataframe.at[
                index,
                "transformation_notes",
            ] = note

        elif note not in str(existing):
            dataframe.at[
                index,
                "transformation_notes",
            ] = f"{existing}; {note}"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data while preserving original records separately."""

    result = df.copy()

    if "transformation_notes" not in result.columns:
        result["transformation_notes"] = ""

    ignored_columns = {
        "source_file",
        "source_row",
        "transformation_notes",
    }

    data_columns = [
        column
        for column in result.columns
        if column not in ignored_columns
    ]

    if data_columns:
        result = result.dropna(
            how="all",
            subset=data_columns,
        ).copy()

    text_columns = result.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:
        if column in ignored_columns:
            continue

        original_values = result[column].copy()

        cleaned_values = (
            result[column]
            .astype("string")
            .str.strip()
        )

        whitespace_changed = (
            original_values
            .astype("string")
            .fillna("")
            .ne(cleaned_values.fillna(""))
        )

        blank_values = cleaned_values.eq("")

        result[column] = cleaned_values.replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "none": pd.NA,
                "null": pd.NA,
            }
        )

        _append_note(
            result,
            whitespace_changed,
            f"Whitespace cleaned in {column}",
        )

        _append_note(
            result,
            blank_values,
            f"Empty {column} converted to missing",
        )

    if "date" in result.columns:
        original_dates = result["date"].copy()

        result["date_original"] = original_dates

        parsed_dates = pd.to_datetime(
            original_dates,
            errors="coerce",
        )

        normalized_dates = parsed_dates.dt.strftime(
            "%Y-%m-%d"
        )

        had_date_value = ~original_dates.map(_is_empty)

        invalid_dates = (
            had_date_value
            & normalized_dates.isna()
        )

        changed_dates = (
            had_date_value
            & ~invalid_dates
            & original_dates
            .astype("string")
            .fillna("")
            .ne(
                normalized_dates
                .astype("string")
                .fillna("")
            )
        )

        result["date"] = normalized_dates

        _append_note(
            result,
            changed_dates,
            "Date standardized to YYYY-MM-DD",
        )

        _append_note(
            result,
            invalid_dates,
            "Invalid date preserved in date_original",
        )

    result["transformation_notes"] = (
        result["transformation_notes"]
        .fillna("")
        .replace("", "No transformation required")
    )

    return result.reset_index(drop=True)


def remove_duplicate_records(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove repeated non-empty person IDs.

    The first record is kept. Original records and duplicate issues
    remain available separately.
    """

    result = df.copy()

    if "person_id" not in result.columns:
        return result.reset_index(drop=True)

    valid_ids = ~result["person_id"].map(_is_empty)

    duplicate_mask = (
        valid_ids
        & result["person_id"].duplicated(
            keep="first"
        )
    )

    result = result.loc[
        ~duplicate_mask
    ].copy()

    return result.reset_index(drop=True)


def find_data_issues(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Find missing values and invalid dates."""

    issues = []

    checks = [
        (
            "person_id",
            "missing_person_id",
            "Missing person ID",
        ),
        (
            "name",
            "missing_name",
            "Missing beneficiary name",
        ),
        (
            "program",
            "missing_program",
            "Missing program name",
        ),
        (
            "outcome",
            "missing_outcome",
            "Missing outcome",
        ),
        (
            "date",
            "missing_date",
            "Missing activity date",
        ),
    ]

    for index, row in df.iterrows():
        source_file = row.get(
            "source_file",
            "unknown",
        )

        source_row = row.get(
            "source_row",
            index + 1,
        )

        for column, issue_type, message in checks:
            if column not in df.columns:
                is_missing = True
            else:
                is_missing = _is_empty(
                    row.get(column)
                )

            if is_missing:
                issues.append(
                    {
                        "type": issue_type,
                        "message": message,
                        "source_file": source_file,
                        "source_row": source_row,
                    }
                )

        if (
            "date_original" in df.columns
            and "date" in df.columns
            and not _is_empty(
                row.get("date_original")
            )
            and _is_empty(row.get("date"))
        ):
            issues.append(
                {
                    "type": "invalid_date",
                    "message": (
                        "Date could not be standardized. "
                        "Original value was preserved."
                    ),
                    "source_file": source_file,
                    "source_row": source_row,
                }
            )

    return issues