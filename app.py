import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Clinical Trial Safety Dashboard", layout="wide")
st.title("Phase III Clinical Trial: Safety & Demographics Monitor")

# --- DATA LOADING (CACHED FOR SPEED) ---
@st.cache_data
def load_data():
    # Pandas can read standard SAS transport files (.xpt) directly
    adsl = pd.read_sas('data/adsl.xpt', format='xport')
    adae = pd.read_sas('data/adae.xpt', format='xport')
    
    # Decode byte strings to standard strings (common when reading xpt in pandas)
    for df in [adsl, adae]:
        for col in df.select_dtypes([object]).columns:
            df[col] = df[col].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)
            
    return adsl, adae

# Load the data
try:
    adsl, adae = load_data()
except FileNotFoundError:
    st.error("Data files not found. Please ensure adsl.xpt and adae.xpt are in the 'data' folder.")
    st.stop()

# --- SIDEBAR: FILTERS ---
st.sidebar.header("Filter Controls")

# Site Filter
site_list = ["All"] + sorted(adsl['SITEID'].dropna().unique().tolist())
selected_site = st.sidebar.selectbox("Select Site (SITEID):", site_list)

# Subject Filter
if selected_site != "All":
    filtered_adsl = adsl[adsl['SITEID'] == selected_site]
else:
    filtered_adsl = adsl

subject_list = ["All"] + sorted(filtered_adsl['USUBJID'].dropna().unique().tolist())
selected_subject = st.sidebar.selectbox("Select Subject (USUBJID):", subject_list)

# --- REACTIVE DATA FILTERING ---
# Apply filters to ADSL
if selected_site != "All":
    adsl = adsl[adsl['SITEID'] == selected_site]
if selected_subject != "All":
    adsl = adsl[adsl['USUBJID'] == selected_subject]

# Filter ADAE based on the subsetted ADSL
adae = adae[adae['USUBJID'].isin(adsl['USUBJID'])]

# --- KPI HEADER ---
col1, col2, col3 = st.columns(3)
total_enrolled = len(adsl)
active_subjects = len(adsl[adsl['SAFFL'] == 'Y']) 
total_saes = len(adae[adae['AESER'] == 'Y'])

with col1:
    st.metric("Total Enrolled (Filtered)", total_enrolled)
with col2:
    st.metric("Safety Population (SAFFL='Y')", active_subjects)
with col3:
    st.metric("Total Serious AEs (AESER='Y')", total_saes)

st.markdown("---")

# --- VISUALIZATIONS ---
viz_col1, viz_col2 = st.columns(2)

with viz_col1:
    st.subheader("Demographic Distribution: Age by Treatment")
    if not adsl.empty:
        # Treatment variable is TRT01A
        fig_age = px.box(adsl, x="TRT01A", y="AGE", points="all", color="TRT01A",
                         labels={"TRT01A": "Treatment Arm", "AGE": "Age"})
        st.plotly_chart(fig_age, use_container_width=True)
    else:
        st.info("No demographic data available for this selection.")

with viz_col2:
    st.subheader("Top Treatment-Emergent AEs")
    # Filter for TEAEs
    teae_df = adae[adae['TRTEMFL'] == 'Y']
    if not teae_df.empty:
        # Get top 10 AEs
        ae_counts = teae_df['AEDECOD'].value_counts().reset_index().head(10)
        ae_counts.columns = ['Adverse Event', 'Count']
        
        fig_ae = px.bar(ae_counts, x='Count', y='Adverse Event', orientation='h',
                        labels={'Count': 'Number of Occurrences', 'Adverse Event': ''})
        fig_ae.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_ae, use_container_width=True)
    else:
        st.info("No Treatment-Emergent AEs found for this selection.")

st.markdown("---")

# --- DATA LISTING ---
st.subheader("Actionable Patient Listing (ADSL + ADAE subset)")

# 1. Drop overlapping demographic columns from ADAE before merging
overlap_cols = [col for col in ['SITEID', 'AGE', 'SEX', 'TRT01A'] if col in adae.columns]
adae_clean = adae.drop(columns=overlap_cols)

# 2. Left join ADAE to ADSL 
merged_data = pd.merge(adae_clean, adsl[['USUBJID', 'SITEID', 'AGE', 'SEX', 'TRT01A']], on='USUBJID', how='left')

# Select only critical variables for the Medical Monitor
display_cols = ['USUBJID', 'SITEID', 'TRT01A', 'AGE', 'SEX', 'AEDECOD', 'AESER', 'TRTEMFL']

if not merged_data.empty:
    st.dataframe(merged_data[display_cols], use_container_width=True)
else:
    st.info("No AE records to display for current filters.")