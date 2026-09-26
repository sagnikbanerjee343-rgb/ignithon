import streamlit as st
import pandas as pd
import io

# ==========================================
# 1. PAGE CONFIGURATION & PREMIUM CSS INJECTION
# ==========================================
st.set_page_config(page_title="Impact Reporting", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Font & Background */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }
    .stApp {
        background-color: #f4f2ee;
    }
    
    /* Remove default top padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Custom Dark Header Card */
    .hero-card {
        background-color: #1a1a1a;
        padding: 2.5rem;
        border-radius: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15);
        margin-bottom: 2rem;
        border-left: 8px solid #fde047;
    }
    .hero-card h1 {
        color: #ffffff !important;
        font-weight: 800 !important;
        margin-bottom: 0.5rem !important;
        font-size: 2.5rem !important;
    }
    .hero-card p {
        color: #9ca3af !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Metric Cards Styling */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 1.5rem;
        border-radius: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #fde047;
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280 !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        font-size: 0.8rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #1a1a1a !important;
        font-weight: 800 !important;
        font-size: 2.5rem !important;
    }

    /* File Uploader Customization */
    [data-testid="stFileUploadDropzone"] {
        background-color: #ffffff !important;
        border: 2px dashed #1a1a1a !important;
        border-radius: 20px !important;
        padding: 2rem !important;
    }
    
    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 12px 12px 0 0;
        border: 1px solid #e5e7eb;
        border-bottom: none;
        padding: 12px 24px;
        font-weight: 600;
        color: #4b5563;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a1a1a !important;
        color: #fde047 !important;
        border-color: #1a1a1a !important;
    }
    
    /* Button Customization */
    .stButton > button {
        background-color: #1a1a1a !important;
        color: #fde047 !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        padding: 0.5rem 2rem !important;
    }
    .stButton > button:hover {
        background-color: #000000 !important;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SIDEBAR NAVIGATION (Fake CampusLife feel)
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    st.markdown("Manage your nonprofit data processing pipeline.")
    st.markdown("---")
    st.info("💡 **Tip:** Upload multiple files at once (CSV, JSON, Excel) to cross-reference data automatically.")
    st.markdown("---")
    st.markdown("**Team Project:** Ignithon Hackathon")

# ==========================================
# 3. HERO HEADER
# ==========================================
st.markdown("""
    <div class="hero-card">
        <h1>Traceable Impact Reporting</h1>
        <p>Core Engine: Systematically combine, clean, and analyze operational files for small nonprofits.</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 4. FILE UPLOADER & LOGIC
# ==========================================
uploaded_files = st.file_uploader("Drop your organization's dataset here", type=["csv", "json", "xlsx"], accept_multiple_files=True)

if uploaded_files:
    file_names = [file.name for file in uploaded_files]
    st.success(f"✅ Successfully loaded {len(uploaded_files)} files: {', '.join(file_names)}")
    
    # --- DOST KE FUNCTIONS YAHAN AAYENGE LATER ---
    # df = dp.read_uploaded_file(uploaded_files)
    # df = dp.standardize_columns(df)
    # ... 
    
    # Mock Data for UI presentation
    metrics = {
        "row_count": 1250,
        "total_beneficiaries": 4500,
        "programs": 5,
        "positive_outcome_rate": "78%",
        "duplicates": 12,
        "missing_values": 34
    }
    
    issues_df = pd.DataFrame({
        "source_file": ["attendance.csv", "feedback.json", "attendance.csv"],
        "source_row": [42, 105, 89],
        "issue_type": ["Missing Beneficiary ID", "Invalid Date Format", "Duplicate Entry"]
    })
    
    # ==========================================
    # 5. TABBED DASHBOARD (The core UI)
    # ==========================================
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard Overview", "⚠️ Data Quality Issues", "🔍 Source Traceability", "📝 Limitations"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Beneficiaries", f"{metrics['total_beneficiaries']:,}")
            st.metric("Total Rows Processed", f"{metrics['row_count']:,}")
        with col2:
            st.metric("Active Programs", metrics['programs'])
            st.metric("Duplicates Removed", metrics['duplicates'])
        with col3:
            st.metric("Positive Outcome", metrics['positive_outcome_rate'])
            st.metric("Missing Values", metrics['missing_values'])

    with tab2:
        st.markdown("### ⚠️ Data Quality Flags")
        st.write("The system flagged the following anomalies. Check `source_file` and `source_row` for quick fixes.")
        st.dataframe(issues_df, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### 🔍 Source Traceability Mapping")
        st.write("Tracking which metric originated from which specific file.")
        st.info("Backend mapping function will populate this section.")

    with tab4:
        st.markdown("### 📝 System Limitations & Assumptions")
        st.write("- **Assumption:** Blank outcome fields are excluded from the positive rate calculation.")
        st.write("- **Limitation:** Fuzzy matching for names is not applied.")

    # ==========================================
    # 6. DOWNLOAD SECTION
    # ==========================================
    st.markdown("---")
    csv_buffer = io.BytesIO()
    pd.DataFrame({"Status": ["Processed", "Ready"]}).to_csv(csv_buffer, index=False)
    
    st.download_button(
        label="Download Cleaned CSV Report",
        data=csv_buffer.getvalue(),
        file_name="cleaned_nonprofit_report.csv",
        mime="text/csv"
    )

else:
    # Empty state prompt
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👆 Please upload your data files (CSV, JSON, or Excel) in the dropzone above to generate the impact report.")