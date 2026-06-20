import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
import time
from datetime import date, datetime

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full Ledger & Analytics")

db_file = "herbarium_database_expanded.csv"

# 1. INITIALIZE DATABASE WITH HEADERS
base_headers = [
    "Data_Source", "Collector", "Col_Number", "Barcode", "Species", "DOY", "Year",
    "Flowering", "Fruiting", "Vegetative", "Latitude", "Longitude", "Elevation", "URL"
]

if not os.path.exists(db_file):
    pd.DataFrame(columns=base_headers).to_csv(db_file, index=False)

# --- Helpers: API Fetchers & Formatting ---
def get_elevation(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            elevations = res.json().get('elevation')
            if elevations and len(elevations) > 0:
                return float(elevations[0])
    except Exception: 
        return None
    return None

def get_climate_data(lat, lon, el, prd):
    if el is None: return {} 
    base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
    url = f"{base}?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd={prd}&varYSM=YSM"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data[0] if isinstance(data, list) else data
    except Exception: 
        return {}
    return {}

def save_with_ordered_columns(df_to_save, filepath):
    new_order = [c for c in base_headers if c in df_to_save.columns]
    priority_climate = ["Y_MAT", "N_MAT", "Y_MAP", "N_MAP"] 
    new_order += [c for c in priority_climate if c in df_to_save.columns and c not in new_order]
    new_order += [c for c in df_to_save.columns if c not in new_order]
    df_to_save[new_order].to_csv(filepath, index=False)

# --- Layout ---
c1, c2 = st.columns([1, 2.2])

# Column 1: Data Collection
with c1:
    st.subheader("Data Collection")
    tab1, tab2 = st.tabs(["🌿 Herbarium", "🦋 iNaturalist"])
    
    # --- TAB 1: MANUAL HERBARIUM ENTRY ---
    with tab1:
        with st.form("data_entry_form"):
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
            
            submitted = st.form_submit_button("💾 SAVE ENTRY", type="primary", use_container_width=True)
        
        if submitted:
            with st.spinner("Fetching climate models..."):
                year_data = get_climate_data(lat, lon, el, f"Year_{date_
