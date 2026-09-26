import pandas as pd
import streamlit as st

from data_processing import (
    read_uploaded_file,
    standardize_columns,
    clean_dataframe,
    find_data_issues,
)

from metrics import (
    detect_duplicates,
    calculate_metrics,
    create_source_summary,
    create_limitations,
)


st.set_page_config(
    page_title="Impact Reporting",
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
    st.write("Upload nonprofit program files for cleaning and analysis.")
    st.info(
        "Supported formats: CSV, JSON, and Excel."
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
        "Upload one or more CSV, JSON, or Excel files to begin."
    )
    st.stop()


st.success(
    f"{len(uploaded_files)} file(s) uploaded successfully."
)


processed_frames = []
processing_errors = []


for uploaded_file in uploaded_files:
    try:
        dataframe = read_uploaded_file(uploaded_file)
        dataframe = standardize_columns(dataframe)
        dataframe = clean_dataframe(dataframe)
        processed_frames.append(dataframe)

    except Exception as error:
        processing_errors.append(
            f"{uploaded_file.name}: {error}"
        )


if processing_errors:
    st.warning("Some files could not be processed.")

    for error in processing_errors:
        st.error(error)


if not processed_frames:
    st.error("No files could be processed.")
    st.stop()


combined_df = pd.concat(
    processed_frames,
    ignore_index=True,
    sort=False,
)


missing_issues = find_data_issues(combined_df)
duplicate_issues = detect_duplicates(combined_df)

all_issues = missing_issues + duplicate_issues

metrics = calculate_metrics(combined_df)
source_summary = create_source_summary(combined_df)
limitations = create_limitations(
    combined_df,
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


positive_rate = metrics["positive_outcome_rate"]

if positive_rate is None:
    positive_rate_display = "N/A"
else:
    positive_rate_display = f"{positive_rate:.2f}%"


tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Dashboard",
        "Data Quality Issues",
        "Source Traceability",
        "Limitations",
    ]
)


with tab1:
    st.subheader("Dashboard Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Unique Beneficiaries",
            f"{metrics['unique_beneficiaries']:,}",
        )

        st.metric(
            "Total Records",
            f"{metrics['total_records']:,}",
        )

    with col2:
        st.metric(
            "Active Programs",
            metrics["total_programs"],
        )

        st.metric(
            "Duplicate Records",
            metrics["duplicate_count"],
        )

    with col3:
        st.metric(
            "Reported Positive Outcome",
            positive_rate_display,
        )

        st.metric(
            "Missing Values",
            metrics["missing_value_count"],
        )

    st.subheader("Processed Data")

    st.dataframe(
        combined_df,
        use_container_width=True,
        hide_index=True,
    )


with tab2:
    st.subheader("Data Quality Issues")

    if issues_df.empty:
        st.success("No data-quality issues were detected.")
    else:
        st.write(
            "These issues are linked to their original source file "
            "and source row."
        )

        st.dataframe(
            issues_df,
            use_container_width=True,
            hide_index=True,
        )


with tab3:
    st.subheader("Source Traceability")

    if source_summary:
        source_df = pd.DataFrame(
            list(source_summary.items()),
            columns=["source_file", "record_count"],
        )

        st.dataframe(
            source_df,
            use_container_width=True,
            hide_index=True,
        )

    st.write(
        "Each processed record retains its source file and source row."
    )

    traceability_columns = [
        column
        for column in [
            "person_id",
            "name",
            "program",
            "outcome",
            "source_file",
            "source_row",
        ]
        if column in combined_df.columns
    ]

    st.dataframe(
        combined_df[traceability_columns],
        use_container_width=True,
        hide_index=True,
    )


with tab4:
    st.subheader("Limitations and Assumptions")

    for limitation in limitations:
        st.write(f"- {limitation}")


st.divider()

st.subheader("Download Report")

st.download_button(
    label="Download Cleaned CSV Report",
    data=combined_df.to_csv(index=False).encode("utf-8"),
    file_name="cleaned_nonprofit_report.csv",
    mime="text/csv",
)