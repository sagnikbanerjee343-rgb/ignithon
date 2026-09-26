from __future__ import annotations

import re
from typing import Any

import pandas as pd


def _first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column

    return None


def _is_missing(value: Any) -> bool:
    if value is None:
        return True

    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass

    return str(value).strip() == ""


def _normalize_name(value: Any) -> str:
    if _is_missing(value):
        return ""

    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9\s]", "", value)
    value = re.sub(r"\s+", " ", value)

    return value


def _make_issue(
    row: pd.Series,
    row_index: Any,
    issue_type: str,
    message: str,
    person_id: Any = None,
    name: Any = None,
) -> dict[str, Any]:
    return {
        "type": issue_type,
        "message": message,
        "person_id": (
            None
            if _is_missing(person_id)
            else person_id
        ),
        "name": (
            None
            if _is_missing(name)
            else name
        ),
        "source_file": row.get(
            "source_file",
            None,
        ),
        "source_row": row.get(
            "source_row",
            row_index + 1,
        ),
    }


def detect_duplicates(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Find duplicate IDs and repeated names without IDs."""

    issues = []

    person_id_column = _first_existing_column(
        df,
        [
            "person_id",
            "participant_id",
            "beneficiary_id",
        ],
    )

    name_column = _first_existing_column(
        df,
        [
            "name",
            "full_name",
            "participant_name",
            "beneficiary_name",
        ],
    )

    if person_id_column:
        valid_ids = ~df[
            person_id_column
        ].map(_is_missing)

        duplicate_mask = (
            valid_ids
            & df[person_id_column].duplicated(
                keep="first"
            )
        )

        for row_index, row in df[
            duplicate_mask
        ].iterrows():
            person_id = row[
                person_id_column
            ]

            name = (
                row[name_column]
                if name_column
                else None
            )

            issues.append(
                _make_issue(
                    row,
                    row_index,
                    "duplicate_person_id",
                    f"Duplicate person ID detected: {person_id}",
                    person_id,
                    name,
                )
            )

    if name_column:
        normalized_names = df[
            name_column
        ].map(_normalize_name)

        if person_id_column:
            missing_id_mask = df[
                person_id_column
            ].map(_is_missing)
        else:
            missing_id_mask = pd.Series(
                True,
                index=df.index,
            )

        name_counts = normalized_names[
            missing_id_mask
            & normalized_names.ne("")
        ].value_counts()

        repeated_names = set(
            name_counts[
                name_counts > 1
            ].index
        )

        seen_names = set()

        for row_index, row in df.iterrows():
            normalized_name = normalized_names.loc[
                row_index
            ]

            if (
                not missing_id_mask.loc[row_index]
                or normalized_name
                not in repeated_names
            ):
                continue

            if normalized_name in seen_names:
                issues.append(
                    _make_issue(
                        row,
                        row_index,
                        "likely_duplicate_name",
                        (
                            "Likely duplicate based on "
                            f"matching name: {row[name_column]}"
                        ),
                        name=row[name_column],
                    )
                )

            seen_names.add(normalized_name)

    return issues


def detect_conflicts(
    df: pd.DataFrame,
) -> list[dict[str, Any]]:
    """Find different values for the same person ID."""

    issues = []

    person_id_column = _first_existing_column(
        df,
        [
            "person_id",
            "participant_id",
            "beneficiary_id",
        ],
    )

    name_column = _first_existing_column(
        df,
        [
            "name",
            "full_name",
            "beneficiary_name",
        ],
    )

    if not person_id_column:
        return issues

    valid_ids = ~df[
        person_id_column
    ].map(_is_missing)

    usable_df = df.loc[valid_ids]

    fields_to_check = [
        "program",
        "outcome",
        "location",
        "date",
    ]

    for person_id, group in usable_df.groupby(
        person_id_column
    ):
        for field in fields_to_check:
            if field not in group.columns:
                continue

            values = group[field].map(
                lambda value: (
                    ""
                    if _is_missing(value)
                    else str(value).strip()
                )
            )

            non_empty_values = values[
                values != ""
            ]

            unique_values = (
                non_empty_values
                .str.lower()
                .unique()
            )

            if len(unique_values) <= 1:
                continue

            display_values = sorted(
                set(non_empty_values.tolist())
            )

            message = (
                f"Conflicting {field} values for "
                f"person ID {person_id}: "
                f"{', '.join(display_values)}"
            )

            for row_index, row in group.iterrows():
                name = (
                    row[name_column]
                    if name_column
                    else None
                )

                issues.append(
                    _make_issue(
                        row,
                        row_index,
                        f"conflicting_{field}",
                        message,
                        person_id,
                        name,
                    )
                )

    return issues


def calculate_metrics(
    df: pd.DataFrame,
) -> dict[str, Any]:
    """Calculate descriptive metrics."""

    duplicate_issues = detect_duplicates(df)
    conflict_issues = detect_conflicts(df)

    person_id_column = _first_existing_column(
        df,
        [
            "person_id",
            "participant_id",
            "beneficiary_id",
        ],
    )

    program_column = _first_existing_column(
        df,
        [
            "program",
            "program_name",
            "program_id",
        ],
    )

    outcome_column = _first_existing_column(
        df,
        [
            "outcome",
            "positive_outcome",
            "outcome_status",
            "result",
            "completed",
        ],
    )

    if person_id_column:
        valid_people = df.loc[
            ~df[person_id_column].map(
                _is_missing
            ),
            person_id_column,
        ]

        unique_beneficiaries = int(
            valid_people.nunique()
        )
    else:
        unique_beneficiaries = 0

    if program_column:
        valid_programs = df.loc[
            ~df[program_column].map(
                _is_missing
            ),
            program_column,
        ]

        total_programs = int(
            valid_programs.nunique()
        )
    else:
        total_programs = 0

    positive_outcomes = 0
    positive_outcome_rate = None

    if outcome_column:
        outcomes = df.loc[
            ~df[outcome_column].map(
                _is_missing
            ),
            outcome_column,
        ].astype(str).str.strip().str.lower()

        excluded_values = {
            "not recorded",
            "not available",
            "unknown",
            "n/a",
            "na",
        }

        outcomes = outcomes[
            ~outcomes.isin(excluded_values)
        ]

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
            outcomes.isin(
                positive_values
            ).sum()
        )

        if len(outcomes) > 0:
            positive_outcome_rate = round(
                positive_outcomes
                / len(outcomes)
                * 100,
                2,
            )

    ignored_columns = {
        "source_file",
        "source_row",
        "transformation_notes",
        "date_original",
    }

    data_columns = [
        column
        for column in df.columns
        if column not in ignored_columns
    ]

    missing_value_count = int(
        df[data_columns]
        .isna()
        .sum()
        .sum()
    )

    return {
        "total_records": int(len(df)),
        "unique_beneficiaries": unique_beneficiaries,
        "total_programs": total_programs,
        "positive_outcomes": positive_outcomes,
        "positive_outcome_rate": positive_outcome_rate,
        "duplicate_count": len(duplicate_issues),
        "conflict_count": len(conflict_issues),
        "missing_value_count": missing_value_count,
    }


def create_source_summary(
    df: pd.DataFrame,
) -> dict[str, int]:
    if "source_file" not in df.columns:
        return {}

    source_values = (
        df["source_file"]
        .fillna("Unknown source")
        .astype(str)
        .str.strip()
        .replace("", "Unknown source")
    )

    return {
        str(source): int(count)
        for source, count in source_values.value_counts().items()
    }


def create_summary_report(
    df: pd.DataFrame,
    issues: list[dict[str, Any]],
    source_summary: dict[str, int],
) -> pd.DataFrame:
    metrics = calculate_metrics(df)

    return pd.DataFrame(
        [
            {
                "metric": "Files processed",
                "value": len(source_summary),
            },
            {
                "metric": "Total cleaned records",
                "value": metrics["total_records"],
            },
            {
                "metric": "Unique beneficiaries",
                "value": metrics[
                    "unique_beneficiaries"
                ],
            },
            {
                "metric": "Active programs",
                "value": metrics["total_programs"],
            },
            {
                "metric": "Positive outcomes",
                "value": metrics[
                    "positive_outcomes"
                ],
            },
            {
                "metric": "Reported positive outcome rate",
                "value": (
                    "N/A"
                    if metrics[
                        "positive_outcome_rate"
                    ] is None
                    else (
                        f'{metrics["positive_outcome_rate"]:.2f}%'
                    )
                ),
            },
            {
                "metric": "Duplicate records removed",
                "value": metrics["duplicate_count"],
            },
            {
                "metric": "Conflicting records",
                "value": metrics["conflict_count"],
            },
            {
                "metric": "Missing values",
                "value": metrics[
                    "missing_value_count"
                ],
            },
            {
                "metric": "Total flagged issues",
                "value": len(issues),
            },
        ]
    )


def create_limitations(
    df: pd.DataFrame,
    issues: list[dict[str, Any]],
) -> list[str]:
    issue_types = {
        issue.get("type", "")
        for issue in issues
    }

    limitations = []

    if any(
        issue_type.startswith("missing_")
        for issue_type in issue_types
    ):
        limitations.append(
            "Some records contain missing information."
        )

    if any(
        issue_type.startswith("duplicate")
        or issue_type.startswith("likely_duplicate")
        for issue_type in issue_types
    ):
        limitations.append(
            "Duplicate records were removed from the cleaned view."
        )

    if any(
        issue_type.startswith("conflicting_")
        for issue_type in issue_types
    ):
        limitations.append(
            "Some records contain conflicting values across sources."
        )

    if "invalid_date" in issue_types:
        limitations.append(
            "Some dates could not be standardized."
        )

    limitations.extend(
        [
            "The uploaded data may not represent all nonprofit activity.",
            "The reported positive outcome rate is descriptive.",
            "The data does not prove that the program caused the outcomes.",
            "Original records remain available for review.",
        ]
    )

    return limitations