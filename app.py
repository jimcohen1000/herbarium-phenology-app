import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.title("Herbarium Tracker - Dual Climate Sync")

# Expanded headers to hold both specific year and baseline normal metrics
headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", "MAT_Year", "MAT_Normal", "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

# Safe database initializer
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
        st.success("Database table completely cleared!")
        st.rerun()

# ----------------- MAIN LAYOUT COLUMNS -----------------
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    
    chosen_date = st.date_input("Collection Date", value=date(2020, 5, 1))
    yr = chosen_date.year
    doy = int(chosen_date.strftime("%j"))
    
    st.info(f"📅 DOY: **{doy}** | Year: **{yr}**")
    
    st.write("**Phenology Status (Select all that apply):**")
    is_flowering = st.checkbox("Flowering", value=True)
    is_fruiting = st.checkbox("Fruiting", value=False)
    is_vegetative = st.checkbox("None (Vegetative Only)", value=False)
    
    lat = st.number_input("Latitude", format="%.5f", value=51.17641)
    lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
    el = st.number_input("Elevation (meters)", min_value=0, value=1420)
    
    btn = st.button("Save & Link Climate Data")
    
    if btn:
        q_yr = 2024 if yr > 2024 else (1901 if yr < 1901 else yr)
        
        # FIXED: Removed trailing extensions to map directly to server expectations
        url_year = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{q_yr}&varYSM=YSM"
        url_norm = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=YSM"
        
        mat_year = "Data Unavailable"
        mat_norm = "Data Unavailable"
        diagnostic_log = {}

        # CALL 1 SATELLITE: Completely isolated historical target loop
        try:
            res_yr = requests.get(url_year, timeout=10)
            if res_yr.status_code == 200:
                data_yr = res_yr.json()
                diagnostic_log["Year_API_Raw"] = data_yr
                dict_yr = data_yr[0] if isinstance(data_yr, list) else data_yr
                if "MAT" in dict_yr and float(dict_yr["MAT"]) != -9999.0:
                    mat_year = float(dict_yr["MAT"])
            else:
                diagnostic_log["Year_API_Error"] = f"HTTP {res_yr.status_code}"
        except Exception as e:
            diagnostic_log["Year_API_Exception"] = str(e)

        # CALL 2 SATELLITE: Completely isolated reference normal baseline loop
        try:
            res_nm = requests.get(url_norm, timeout=10)
            if res_nm.status_code == 200:
                data_nm = res_nm.json()
                diagnostic_log["Normal_API_Raw"] = data_nm
                dict_nm = data_nm[0] if isinstance(data_nm, list) else data_nm
                if "MAT" in dict_nm and float(dict_nm["MAT"]) != -9999.0:
                    mat_norm = float(dict_nm["MAT"])
            else:
                diagnostic_log["Normal_API_Error"] = f"HTTP {res_nm.status_code}"
        except Exception as e:
            diagnostic_log["Normal_API_Exception"] = str(e)
            
        st.session_state.last_raw_response = diagnostic_log
            
        # Compile row with dual temperature indicators
        row = pd.DataFrame([[
            spp, doy, yr, lat, lon, el,
            is_flowering, is_fruiting, is_vegetative,
            mat_year, mat_norm, "Herbarium"
        ]], columns=headers)
        
        row.to_csv(db_file, mode='a', header=False, index=False)
        st.success("Retrieval processing complete!")
        st.rerun()

with c2:
    st.subheader("Diagnostics & Visualizations")
    
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console", expanded=True):
            st.json(st.session_state.last_raw_response)
        
    try:
        df = pd.read_csv(db_file)
    except Exception:
        df = pd.DataFrame(columns=headers)
        
    if df.empty:
        st.info("No records found yet.")
    else:
        st.write("**Current Ledger View:**")
        st.dataframe(df, use_container_width=True)
        
        # Prepare numbers safely for trends chart
        plot_df = df.copy()
        plot_df["MAT_Year"] = pd.to_numeric(plot_df["MAT_Year"], errors='coerce')
        plot_df = plot_df.dropna(subset=["MAT_Year"])
        
        if not plot_df.empty:
            fig = px.scatter(
                plot_df, 
                x="MAT_Year", 
                y="DOY", 
                color="Year",
                hover_data=["MAT_Normal", "Flowering", "Fruiting", "Vegetative"],
                title="Phenology Trends vs Collection Year Temperature"
            )
            st.plotly_chart(fig, use_container_width=True)
