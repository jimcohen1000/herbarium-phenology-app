import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full Ledger & Analytics")

db_file = "herbarium_database_expanded.csv"

# 1. ALWAYS INITIALIZE THE DATABASE WITH HEADERS
base_headers = [
    "Collector", "Col_Number", "Barcode", "Species", "DOY", "Year",
    "Flowering", "Fruiting", "Vegetative", "Latitude", "Longitude", "Elevation"
]

# Create the file immediately if it doesn't exist so the table shows up
if not os.path.exists(db_file):
    pd.DataFrame(columns=base_headers).to_csv(db_file, index=False)

# --- Helper: Climate Data Fetcher ---
def get_climate_data(lat, lon, el, prd):
    base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
    url = f"{base}?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd={prd}&varYSM=YSM"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data[0] if isinstance(data, list) else data
    except: return {}
    return {}

# --- Layout ---
c1, c2 = st.columns([1, 2.2])

# Column 1: Data Collection
with c1:
    st.subheader("Data Collection")
    collector = st.text_input("Collector Name")
    col_num = st.text_input("Collector Number")
    barcode = st.text_input("Barcode")
    spp = st.text_input("Species")
    date_val = st.date_input("Date", min_value=date(1900, 1, 1), max_value=date(2030, 12, 31), value=date(2020, 5, 1))
    
    st.write("**Phenology:**")
    col_f, col_fr, col_v = st.columns(3)
    with col_f: flow = st.checkbox("Flowering", value=True)
    with col_fr: fruit = st.checkbox("Fruiting")
    with col_v: veg = st.checkbox("Vegetative")
    
    lat = st.number_input("Lat", format="%.5f", value=51.1764)
    lon = st.number_input("Lon", format="%.5f", value=-115.5682)
    el = st.number_input("Elev (m)", value=1420)
    
    if st.button("Save Entry", use_container_width=True):
        with st.spinner("Fetching climate models..."):
            year_data = get_climate_data(lat, lon, el, f"Year_{date_val.year}")
            norm_
