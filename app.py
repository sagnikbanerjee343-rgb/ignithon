import pandas as pd
import streamlit as st

from data_processing import (
    read_uploaded_file,
    standardize_columns,
    clean_dataframe,
    find_data_issues,
    remove_duplicate_records,
)

from metrics import (
    detect_duplicates,
    detect_conflicts,
    calculate_metrics,
    create_source_summary,
    create_summary_report,
    create_limitations,
)


st.set_page_config(
    page_title="Traceable Impact Reporting",
    layout="wide",
)


st.markdown(
    """
    <style>
    .stApp {
        background-color: #f4f2ee;
    }

    .hero {
        background-color: #1a1a1a;
        padding: 2rem;
        border-radius: 18px;
        margin-bottom: 2rem;
        border-left: 8px solid #fde047;
    }

    .hero h1 {
        color: white;
        margin-bottom: 0.5rem;
    }

    .hero p {
        color: #d1d5db;
        font-size: 1.05rem;
    }

    [data-testid="stMetric"] {
        background-color: white;
        padding: 1rem;
        border-radius: 15px;
        border: 1px solid #e5e7eb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.title("Control Panel")

    st.write(
        "Upload nonprofit files for cleaning, checking, and reporting."
    )

    st.info(
        "Use synthetic or sample data. "
        "Do not upload sensitive beneficiary information."
    )


st.markdown(
    """
    <div class="hero">
        <h1>Traceable Impact Reporting</h1>
        <p>
            Combine, clean, analyze, and trace nonprofit program data
            from multiple sources.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


uploaded_files = st.file_uploader(
    "Upload nonprofit data files",
    type=["csv", "json", "xlsx", "xls"],
    accept_multiple_files=True,
)


if not uploaded_files:
    st.info(
        "Upload CSV, JSON, or Excel files to begin."
    )
    st.stop()


raw_frames = []
processed_frames = []
processing_errors = []


for uploaded_file in uploaded_files:
    try:
        raw_dataframe = read_uploaded_file(
            uploaded_file
        )

        raw_frames.append(
            raw_dataframe.copy()
        )

        processed_dataframe = standardize_columns(
            raw_dataframe.copy()
        )

        processed_dataframe = clean_dataframe(
            processed_dataframe
        )

        processed_frames.append(
            processed_dataframe
        )

    except Exception as error:
        processing_errors.append(
            f"{uploaded_file.name}: {error}"
        )


if processing_errors:
    st.warning(
        "Some files could not be processed."
    )

    for error in processing_errors:
        st.error(error)


if not processed_frames:
    st.error(
        "No files could be processed."
    )
    st.stop()


raw_combined_df = pd.concat(
    raw_frames,
    ignore_index=True,
    sort=False,
)

all_processed_records_df = pd.concat(
    processed_frames,
    ignore_index=True,
    sort=False,
)


missing_issues = find_data_issues(
    all_processed_records_df
)

duplicate_issues = detect_duplicates(
    all_processed_records_df
)

conflict_issues = detect_conflicts(
    all_processed_records_df
)

all_issues = (
    missing_issues
    + duplicate_issues
    + conflict_issues
)


cleaned_combined_df = remove_duplicate_records(
    all_processed_records_df
)


metrics = calculate_metrics(
    cleaned_combined_df
)

metrics["duplicate_count"] = len(
    duplicate_issues
)

metrics["conflict_count"] = len(
    conflict_issues
)


source_summary = create_source_summary(
    all_processed_records_df
)


summary_df = create_summary_report(
    cleaned_combined_df,
    all_issues,
    source_summary,
)


summary_df.loc[
    summary_df["metric"]
    == "Duplicate records removed",
    "value",
] = len(duplicate_issues)


summary_df.loc[
    summary_df["metric"]
    == "Conflicting records",
    "value",
] = len(conflict_issues)


limitations = create_limitations(
    cleaned_combined_df,
    all_issues,
)


issues_df = pd.DataFrame(
    all_issues,
    columns=[
        "type",
        "message",
        "person_id",
        "name",
        "source_file",
        "source_row",
    ],
)


if "person_id" in all_processed_records_df.columns:
    valid_ids = (
        all_processed_records_df["person_id"]
        .notna()
    )

    removed_duplicate_rows = (
        all_processed_records_df[
            valid_ids
            & all_processed_records_df[
                "person_id"
            ].duplicated(keep="first")
        ]
        .copy()
    )
else:
    removed_duplicate_rows = pd.DataFrame()


positive_rate = metrics[
    "positive_outcome_rate"
]

if positive_rate is None:
    positive_rate_display = "N/A"
else:
    positive_rate_display = (
        f"{positive_rate:.2f}%"
    )


st.success(
    f"{len(uploaded_files)} file(s) processed successfully."
)


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Summary Report",
        "Original Records",
        "Cleaned Records",
        "Data Quality",
        "Traceability",
        "Limitations",
    ]
)


with tab1:
    st.subheader("Summary Report")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Unique Beneficiaries",
            f"{metrics['unique_beneficiaries']:,}",
        )

        st.metric(
            "Cleaned Records",
            f"{len(cleaned_combined_df):,}",
        )

    with col2:
        st.metric(
            "Active Programs",
            metrics["total_programs"],
        )

        st.metric(
            "Duplicates Removed",
            len(duplicate_issues),
        )

    with col3:
        st.metric(
            "Conflicting Records",
            len(conflict_issues),
        )

        st.metric(
            "Reported Positive Outcome",
            positive_rate_display,
        )

    st.dataframe(
        summary_df,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Metric Definitions"):
        st.markdown(
            """
            **Unique Beneficiaries**  
            Distinct non-empty person IDs after cleaning.

            **Cleaned Records**  
            Records remaining after repeated person IDs were removed.

            **Duplicates Removed**  
            Repeated records after the first occurrence of a person ID.

            **Conflicting Records**  
            Records where the same person has different values
            across uploaded files.

            **Reported Positive Outcome Rate**  
            Positive outcomes divided by recorded outcomes.

            These metrics describe the uploaded data. They do not
            prove overall program impact.
            """
        )


with tab2:
    st.subheader("Original Records")

    st.info(
        "All uploaded records are preserved here, including duplicates."
    )

    st.dataframe(
        raw_combined_df,
        use_container_width=True,
        hide_index=True,
    )


with tab3:
    st.subheader("Cleaned Records")

    st.info(
        "Only the first record for each valid person_id is retained."
    )

    st.dataframe(
        cleaned_combined_df,
        use_container_width=True,
        hide_index=True,
    )


with tab4:
    st.subheader("Data Quality Issues")

    if issues_df.empty:
        st.success(
            "No data-quality issues were detected."
        )
    else:
        st.dataframe(
            issues_df,
            use_container_width=True,
            hide_index=True,
        )

    if not removed_duplicate_rows.empty:
        st.subheader(
            "Records Removed from Cleaned Data"
        )

        st.info(
            "These duplicate rows were removed from the cleaned "
            "view but remain available in Original Records."
        )

        st.dataframe(
            removed_duplicate_rows,
            use_container_width=True,
            hide_index=True,
        )


with tab5:
    st.subheader("Source Traceability")

    source_df = pd.DataFrame(
        list(source_summary.items()),
        columns=[
            "source_file",
            "record_count",
        ],
    )

    st.dataframe(
        source_df,
        use_container_width=True,
        hide_index=True,
    )

    traceability_columns = [
        column
        for column in [
            "person_id",
            "name",
            "program",
            "outcome",
            "date",
            "source_file",
            "source_row",
            "transformation_notes",
        ]
        if column in cleaned_combined_df.columns
    ]

    st.subheader("Cleaned Record Traceability")

    st.dataframe(
        cleaned_combined_df[
            traceability_columns
        ],
        use_container_width=True,
        hide_index=True,
    )


with tab6:
    st.subheader("Limitations and Assumptions")

    for limitation in limitations:
        st.write(f"- {limitation}")


st.divider()

st.subheader("Download Reports")

col1, col2, col3 = st.columns(3)

with col1:
    st.download_button(
        label="Download Cleaned Records",
        data=cleaned_combined_df
        .to_csv(index=False)
        .encode("utf-8"),
        file_name="cleaned_nonprofit_records.csv",
        mime="text/csv",
    )

with col2:
    st.download_button(
        label="Download Summary Report",
        data=summary_df
        .to_csv(index=False)
        .encode("utf-8"),
        file_name="nonprofit_summary_report.csv",
        mime="text/csv",
    )

with col3:
    st.download_button(
        label="Download Issue Report",
        data=issues_df
        .to_csv(index=False)
        .encode("utf-8"),
        file_name="nonprofit_data_quality_issues.csv",
        mime="text/csv",
    )