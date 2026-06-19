import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full Ledger & Analytics")

db_file = "herbarium_database_expanded.csv"

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
# Slightly expanded the right column so the table has more breathing room
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
            norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
            
            row = {
                "Collector": collector, "Col_Number": col_num, "Barcode": barcode,
                "Species": spp, "DOY": int(date_val.strftime("%j")), "Year": date_val.year,
                "Flowering": flow, "Fruiting": fruit, "Vegetative": veg
            }
            for k, v in year_data.items(): row[f"Y_{k}"] = v
            for k, v in norm_data.items(): row[f"N_{k}"] = v
            
            df_new = pd.DataFrame([row])
            if not os.path.exists(db_file): df_new.to_csv(db_file, index=False)
            else: df_new.to_csv(db_file, mode='a', header=False, index=False)
            st.success("Entry saved!")
            st.rerun()

# Column 2: Graphing & Database
with c2:
    st.subheader("Analysis Dashboard")
    if os.path.exists(db_file):
        df = pd.read_csv(db_file)
        climate_vars = [col for col in df.columns if col.startswith('Y_') or col.startswith('N_')]
        
        # Graph Controls
        g1, g2 = st.columns(2)
        with g1: x_var = st.selectbox("Select Climate Variable:", climate_vars)
