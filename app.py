import streamlit as st
import requests
import pandas as pd
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full YSM Climate Ledger")

db_file = "herbarium_database_expanded.csv"

# --- Helper: Initialize Data ---
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

# --- Entry Form ---
c1, c2 = st.columns([1, 1.5])
with c1:
    collector = st.text_input("Collector Name")
    col_num = st.text_input("Collector Number")
    barcode = st.text_input("Barcode")
    spp = st.text_input("Species")
    date_val = st.date_input("Date", min_value=date(1900, 1, 1), max_value=date(2030, 12, 31), value=date(2020, 5, 1))
    flow, fruit, veg = st.checkbox("Flowering"), st.checkbox("Fruiting"), st.checkbox("Vegetative")
    lat = st.number_input("Lat", format="%.5f", value=51.1764)
    lon = st.number_input("Lon", format="%.5f", value=-115.5682)
    el = st.number_input("Elev (m)", value=1420)
    
    if st.button("Save Full Climate Data"):
        # Fetch Year and Normal data
        year_data = get_climate_data(lat, lon, el, f"Year_{date_val.year}")
        norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
        
        # Prepare metadata + dynamic climate variables
        row = {
            "Collector": collector, "Col_Number": col_num, "Barcode": barcode,
            "Species": spp, "DOY": int(date_val.strftime("%j")), "Year": date_val.year,
            "Flowering": flow, "Fruiting": fruit, "Vegetative": veg
        }
        # Append all returned API keys to the row
        for k, v in year_data.items(): row[f"Y_{k}"] = v
        for k, v in norm_data.items(): row[f"N_{k}"] = v
        
        df_new = pd.DataFrame([row])
        if not os.path.exists(db_file): df_new.to_csv(db_file, index=False)
        else: df_new.to_csv(db_file, mode='a', header=False, index=False)
        st.success("Full YSM climate dataset saved!")

# --- Dashboard ---
with c2:
    st.subheader("Expanded Database")
    if os.path.exists(db_file):
        df = pd.read_csv(db_file)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Full CSV", data=df.to_csv(index=False), file_name="full_data.csv")
