import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.title("Herbarium Tracker - Advanced Ledger")

# Expanded data ledger with separate phenology status columns
headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", "MAT", "Data_Source"
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
    
    # Try reading the current dataset size for user reference
    try:
        current_df = pd.read_csv(db_file)
        row_count = len(current_df)
    except Exception:
        current_df = pd.DataFrame(columns=headers)
        row_count = 0
        
    st.metric(label="Total Records Stored", value=row_count)
    
    # Download Button Engine
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
    
    # Wipe/Reset Button Engine
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
    
    # NEW: Separate, distinct phenotype checkboxes
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
        url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=%20Year_{q_yr}.ann&varYSM=YSM"
        
        mat = "Data Unavailable"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                try:
                    st.session_state.last_raw_response = res.json()
                    data = st.session_state.last_raw_response
                    data_dict = data[0] if isinstance(data, list) else data
                    if "MAT" in data_dict and float(data_dict["MAT"]) != -9999.0:
                        mat = float(data_dict["MAT"])
                except Exception:
                    st.session_state.last_raw_response = {"Raw Text": res.text}
            else:
                st.session_state.last_raw_response = {"Error Code": res.status_code, "Message": res.text}
        except Exception as e:
            st.session_state.last_raw_response = {"Connection Error": str(e)}
            
        # Compile row using the new individual boolean column indicators
        row = pd.DataFrame([[
            spp, doy, yr, lat, lon, el,
            is_flowering, is_fruiting, is_vegetative,
            mat, "Herbarium"
        ]], columns=headers)
        
        row.to_csv(db_file, mode='a', header=False, index=False)
        st.success("Point saved successfully!")
        st.rerun()

with c2:
    st.subheader("Diagnostics & Visualizations")
    
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console"):
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
        
        # Clean up column tracking schemas before plotting
        plot_df = df.copy()
        plot_df["MAT"] = pd.to_numeric(plot_df["MAT"], errors='coerce')
        plot_df = plot_df.dropna(subset=["MAT"])
        
        if not plot_df.empty:
            fig = px.scatter(
                plot_df, 
                x="MAT", 
                y="DOY", 
                color="Year",
                hover_data=["Flowering", "Fruiting", "Vegetative"],
                title="Phenology Trends vs Annual Mean Temperature"
            )
            st.plotly_chart(fig, use_container_width=True)
