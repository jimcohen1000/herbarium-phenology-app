import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker - Enhanced Climate Ledger")

# Fully expanded database ledger columns
headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", 
    "MAT_Year", "Tave_WT_Year", "Tave_SP_Year", "Tave_SM_Year", "Tave_05_Year",
    "MAT_Normal", "Tave_WT_Normal", "Tave_SP_Normal", "Tave_SM_Normal", "Tave_05_Normal",
    "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

# Safe database initialization
if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)
else:
    try:
        test_df = pd.read_csv(db_file)
        if len(test_df.columns) != len(headers):
            pd.DataFrame(columns=headers).to_csv(db_file, index=False)
    except Exception:
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# ----------------- SIDEBAR CONTROLS (DOWNLOAD & RESET) -----------------
with st.sidebar:
    st.header("⚙️ Database Controls")
    
    try:
        current_df = pd.read_csv(db_file)
        row_count = len(current_df)
    except Exception:
        current_df = pd.DataFrame(columns=headers)
        row_count = 0
        
    st.metric(label="Total Records Stored", value=row_count)
    
    if row_count > 0:
        csv_data = current_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Database (CSV)",
            data=csv_data,
            file_name="herbarium_phenology_data.csv",
            mime="text/csv"
        )
    else:
        st.button("📥 Download Database (CSV)", disabled=True)
        
    st.write("---")
    
    if st.button("⚠️ Wipe & Reset Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.session_state.last_raw_response = None
        st.success("Database table completely cleared!")
        st.rerun()

# ----------------- MAIN LAYOUT COLUMNS -----------------
c1, c2 = st.columns([1, 1.4])

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    
    chosen_date = st.date_input("Collection Date", value=date(2020, 5, 1))
