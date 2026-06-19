import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- Configuration ---
st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Research Ledger")

# Updated Headers
headers = [
    "Collector", "Col_Number", "Barcode", "Species", "DOY", "Year", 
    "Latitude", "Longitude", "Elevation", "Flowering", "Fruiting", 
    "Vegetative", "MAT_Year", "MAT_Normal", "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("⚠️ Wipe Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.rerun()

# --- Entry Form ---
c1, c2 = st.columns([1, 1.5])

with c1:
    st.subheader("Manual Data Entry")
    collector = st.text_input("Collector Name")
    col_num = st.text_input("Collector Number")
    barcode = st.text_input("Barcode")
    spp = st.text_input("Species")
    
    # Year range extended to 1900-2030
    date_val = st.date_input("Date", min_value=date(1900, 1, 1), max_value=date(2030, 12, 31), value=date(2020, 5, 1))
    yr, doy = date_val.year, int(date_val.strftime("%j"))
    
    flow, fruit, veg = st.checkbox("Flowering"), st.checkbox("Fruiting"), st.checkbox("Vegetative")
    
    lat = st.number_input("Lat", format="%.5f", value=51.1764)
    lon = st.number_input("Lon", format="%.5f", value=-115.5682)
    el = st.number_input("Elev (m)", value=1420)
    
    if st.button("Save Entry"):
        base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
        # Standardized ClimateNA parameter structure
        u_yr = f"{base}?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{yr}&varYSM=Y"
        u_nm = f"{base}?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=Y"
        
        def fetch(u):
            try:
                res = requests.get(u, timeout=10)
                if res.status_code == 200:
                    d = res.json()[0] if isinstance(res.json(), list) else res.json()
                    val = d.get("MAT")
                    return float(val) if val is not None and float(val) != -9999.0 else None
            except: return None
            return None

        mat_year = fetch(u_yr)
        mat_norm = fetch(u_nm)
        
        new_row = [collector, col_num, barcode, spp, doy, yr, lat, lon, el, 
                   flow, fruit, veg, mat_year, mat_norm, "Herbarium"]
        pd.DataFrame([new_row], columns=headers).to_csv(db_file, mode='a', header=False, index=False)
        st.success("Entry saved!")

# --- Dashboard ---
with c2:
    st.subheader("Database")
    df = pd.read_csv(db_file)
    st.dataframe(df)
    
    if not df.empty and df["MAT_Year"].notnull().any():
        fig = px.scatter(df, x="MAT_Year", y="MAT_Normal", color="Year", title="Annual vs Normal Temp")
        st.plotly_chart(fig, use_container_width=True)
