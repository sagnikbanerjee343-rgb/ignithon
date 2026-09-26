from __future__ import annotations

import re
from typing import Any

import pandas as pd


def _first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    """Return the first candidate column that exists in the DataFrame."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def _is_missing(value: Any) -> bool:
    """Safely determine whether a value is missing."""
    return pd.isna(value) or str(value).strip() == ""


def _normalize_name(value: Any) -> str:
    """Normalize a name for simple exact matching."""
    if _is_missing(value):
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value)

    return value


def _get_source_row(row: pd.Series, fallback: Any) -> Any:
    """Use source_row when available, otherwise use the DataFrame index."""
    for column in ("source_row", "source_row_number", "row_number"):
        if column in row.index and not _is_missing(row[column]):
            return row[column]

    return fallback


def _make_issue(
    row: pd.Series,
    row_index: Any,
    issue_type: str,
    message: str,
    person_id: Any = None,
    name: Any = None,
) -> dict[str, Any]:
    """Create a consistently shaped issue dictionary."""
    source_file = (
        row.get("source_file")
        if "source_file" in row.index
        else None
    )

    return {
        "type": issue_type,
        "message": message,
        "person_id": None if _is_missing(person_id) else person_id,
        "name": None if _is_missing(name) else name,
        "source_file": (
            None if _is_missing(source_file) else source_file
        ),
        "source_row": _get_source_row(row, row_index),
    }


def detect_duplicates(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Detect duplicate person IDs and likely duplicates with missing IDs.

    Exact duplicate person IDs are reported for each repeated row after
    the first occurrence.

    When person_id is missing, records with the same normalized name are
    treated as likely duplicates. This intentionally uses exact normalized
    name matching instead of fuzzy matching to keep the function simple
    and dependency-free.
    """
    issues: list[dict[str, Any]] = []

    person_id_column = _first_existing_column(
        df,
        ["person_id", "participant_id", "beneficiary_id"],
    )
    name_column = _first_existing_column(
        df,
        ["name", "full_name", "participant_name", "beneficiary_name"],
    )

    if person_id_column is not None:
        valid_ids = df[person_id_column].where(
            ~df[person_id_column].isna()
        )

        duplicate_id_mask = valid_ids.notna() & valid_ids.duplicated(
            keep="first"
        )

        for row_index, row in df[duplicate_id_mask].iterrows():
            person_id = row[person_id_column]
            name = row[name_column] if name_column else None

            issues.append(
                _make_issue(
                    row=row,
                    row_index=row_index,
                    issue_type="duplicate_person_id",
                    message=(
                        f"Duplicate person_id detected: {person_id}"
                    ),
                    person_id=person_id,
                    name=name,
                )
            )

    if name_column is not None:
        normalized_names = df[name_column].map(_normalize_name)

        missing_id_mask = pd.Series(
            True,
            index=df.index,
        )

        if person_id_column is not None:
            missing_id_mask = df[person_id_column].map(_is_missing)

        name_counts = normalized_names[
            missing_id_mask & normalized_names.ne("")
        ].value_counts()

        likely_duplicate_names = set(
            name_counts[name_counts > 1].index
        )

        reported_name_rows: dict[str, int] = {}

        for row_index, row in df.iterrows():
            normalized_name = normalized_names.loc[row_index]

            if (
                not missing_id_mask.loc[row_index]
                or normalized_name not in likely_duplicate_names
            ):
                continue

            occurrence = reported_name_rows.get(normalized_name, 0)
            reported_name_rows[normalized_name] = occurrence + 1

            # Report each occurrence after the first one.
            if occurrence == 0:
                continue

            name = row[name_column]

            issues.append(
                _make_issue(
                    row=row,
                    row_index=row_index,
                    issue_type="likely_duplicate_name",
                    message=(
                        f"Likely duplicate based on matching name: {name}"
                    ),
                    person_id=None,
                    name=name,
                )
            )

    return issues


def calculate_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Calculate simple descriptive nonprofit program metrics.

    positive_outcome_rate is the reported positive outcome rate.
    It should not be interpreted as overall impact.
    """
    duplicate_issues = detect_duplicates(df)

    person_id_column = _first_existing_column(
        df,
        ["person_id", "participant_id", "beneficiary_id"],
    )

    program_column = _first_existing_column(
        df,
        ["program", "program_name", "program_id"],
    )

    outcome_column = _first_existing_column(
        df,
        [
            "positive_outcome",
            "outcome",
            "outcome_status",
            "result",
            "completed",
        ],
    )

    if person_id_column is not None:
        unique_beneficiaries = int(
            df[person_id_column].dropna().nunique()
        )
    else:
        unique_beneficiaries = 0

    if program_column is not None:
        total_programs = int(
            df[program_column].dropna().nunique()
        )
    else:
        total_programs = 0

    positive_outcomes = 0
    positive_outcome_rate = None

    if outcome_column is not None:
        outcome_values = (
            df[outcome_column]
            .dropna()
            .astype(str)
            .str.strip()
            .str.lower()
        )

        positive_values = {
            "yes",
            "y",
            "true",
            "1",
            "positive",
            "success",
            "successful",
            "completed",
            "complete",
            "improved",
            "achieved",
            "employed",
            "employment",
        }

        positive_outcomes = int(
            outcome_values.isin(positive_values).sum()
        )

        reported_outcome_count = int(len(outcome_values))

        if reported_outcome_count > 0:
            positive_outcome_rate = round(
                positive_outcomes / reported_outcome_count * 100,
                2,
            )

    return {
        "total_records": int(len(df)),
        "unique_beneficiaries": unique_beneficiaries,
        "total_programs": total_programs,
        "positive_outcomes": positive_outcomes,
        # This is the reported positive outcome rate, not overall impact.
        "positive_outcome_rate": positive_outcome_rate,
        "duplicate_count": len(duplicate_issues),
        "missing_value_count": int(df.isna().sum().sum()),
    }


def create_source_summary(df: pd.DataFrame) -> dict[str, int]:
    """
    Return the number of records contributed by each source file.
    """
    source_column = _first_existing_column(
        df,
        ["source_file", "source", "file_name"],
    )

    if source_column is None:
        return {}

    source_values = (
        df[source_column]
        .fillna("Unknown source")
        .astype(str)
        .str.strip()
        .replace("", "Unknown source")
    )

    return {
        str(source): int(count)
        for source, count in source_values.value_counts().items()
    }


def create_limitations(
    df: pd.DataFrame,
    issues: list[dict[str, Any]],
) -> list[str]:
    """
    Return honest limitations based on the available data and issues.
    """
    limitations: list[str] = []

    outcome_column = _first_existing_column(
        df,
        [
            "positive_outcome",
            "outcome",
            "outcome_status",
            "result",
            "completed",
        ],
    )

    if outcome_column is None or df[outcome_column].isna().any():
        limitations.append(
            "Some records have missing outcome data."
        )

    if issues:
        limitations.append(
            "Duplicate records may affect the reported totals."
        )

    if df.empty:
        limitations.append(
            "No records were provided, so the metrics cannot describe "
            "program activity."
        )

    if "source_file" not in df.columns:
        limitations.append(
            "Source-file information is unavailable, so record "
            "provenance may be incomplete."
        )

    limitations.extend(
        [
            "The uploaded files may not represent all nonprofit activities.",
            "The reported positive outcome rate is descriptive and does "
            "not establish that the program caused the outcomes.",
        ]
    )

    return limitations