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
    # 1. Start with your base headers
    new_order = [c for c in base_headers if c in df_to_save.columns]
    
    # 2. Define the highly important climate variables you want pushed to the front
    priority_climate = ["Y_MAT", "N_MAT", "Y_MAP", "N_MAP"] 
    
    # 3. Add priority columns if they exist
    new_order += [c for c in priority_climate if c in df_to_save.columns and c not in new_order]
    
    # 4. Append everything else (the remaining ClimateNA variables)
    new_order += [c for c in df_to_save.columns if c not in new_order]
    
    # 5. Save using the new order
    df_to_save[new_order].to_csv(filepath, index=False)

# --- Layout ---
c1, c2 = st.columns([1, 2.2])

# Column 1: Data Collection
with c1:
    st.subheader("Data Collection")
