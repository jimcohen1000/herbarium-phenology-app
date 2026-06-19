import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- Configuration ---
st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Climate Data Debugger")

headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", "MAT_Year", "MAT_Normal", "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

# Initialize Database
if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("⚠️ Wipe Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.rerun()

# --- Main Interface ---
c1, c2 = st.columns([1, 1.5])

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species", "Anemone patens")
    date_val = st.date_input("Date", min_value=date(1901, 1, 1), value=date(2020, 5, 1))
    yr, doy = date_val.year, int(date_val.strftime("%j"))
    
    flow, fruit, veg = st.checkbox("Flowering"), st.checkbox("Fruiting"), st.checkbox("Vegetative")
    
    lat = st.number_input("Lat", format="%.5f", value=51.1764)
    lon = st.number_input("Lon", format="%.5f", value=-115.5682)
    el = st.number_input("Elev (m)", value=1420)
    
    if st.button("Save Entry"):
        # API Construction
        base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
        
        # NOTE: Using 'Year_YYYY' format for historical data
        url_yr = f"{base}?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{yr}&varYSM=Y"
        url_nm = f"{base}?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=Y"
        
        def fetch_climate_data(url):
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Store raw JSON for diagnosis
                    st.session_state.raw_json = data 
                    d = data[0] if isinstance(data, list) else data
                    # Extract MAT (Mean Annual Temperature)
                    val = d.get("MAT")
                    return float(val) if val is not None and float(val) != -9999.0 else "Unavailable"
                return "Error: " + str(response.status_code)
            except Exception as e:
                return "Exception: " + str(e)

        mat_year = fetch_climate_data(url_yr)
        mat_norm = fetch_climate_data(url_nm)
        
        new_row = [spp, doy, yr, lat, lon, el, flow, fruit, veg, mat_year, mat_norm, "Herbarium"]
        pd.DataFrame([new_row], columns=headers).to_csv(db_file, mode='a', header=False, index=False)
        st.success("Entry saved!")

with c2:
    st.subheader("Diagnostic Console")
    if "raw_json" in st.session_state:
        st.json(st.session_state.raw_json)
    
    st.subheader("Database")
    df = pd.read_csv(db_file)
    st.dataframe(df)
