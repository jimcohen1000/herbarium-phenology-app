import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker - Enhanced Climate Ledger")

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

if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)
else:
    try:
        test_df = pd.read_csv(db_file)
        if len(test_df.columns) != len(headers):
            pd.DataFrame(columns=headers).to_csv(db_file, index=False)
    except Exception:
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.header("⚙️ Controls")
    try:
        current_df = pd.read_csv(db_file)
        row_count = len(current_df)
    except Exception:
        current_df = pd.DataFrame(columns=headers)
        row_count = 0
        
    st.metric("Total Records Stored", row_count)
    
    if row_count > 0:
        csv_data = current_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", data=csv_data, file_name="herbarium_data.csv", mime="text/csv")
    
    if st.button("⚠️ Wipe Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.session_state.last_raw_response = None
        st.rerun()

# ----------------- COLUMNS -----------------
c1, c2 = st.columns([1, 1.4])

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    chosen_date = st.date_input("Collection Date", value=date(2020, 5, 1))
    
    yr = chosen_date.year
    doy = int(chosen_date.strftime("%j"))
    st.info(f"📅 DOY: {doy} | Year: {yr}")
    
    st.write("Phenology Status:")
    is_flowering = st.checkbox("Flowering", value=True)
    is_fruiting = st.checkbox("Fruiting", value=False)
    is_vegetative = st.checkbox("None (Vegetative)", value=False)
    
    lat = st.number_input("Latitude", format="%.5f", value=51.17641)
    lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
    el = st.number_input("Elevation (m)", min_value=0, value=1420)
    
    if st.button("Save Entry"):
        q_yr = 2024 if yr > 2024 else (1901 if yr < 1901 else yr)
        url_year = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{q_yr}.ann&varYSM=YSM"
        url_norm = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=YSM"
        
        def parse_payload(url):
            out = {"MAT": "Data Unavailable", "Tave_wt": "Data Unavailable", "Tave_sp": "Data Unavailable", "Tave_sm": "Data Unavailable", "Tave_05": "Data Unavailable"}
            try:
                res = requests.get(url, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    data_dict = data[0] if isinstance(data, list) else data
                    clean_dict = {str(k).upper().strip(): v for k, v in data_dict.items()}
                    for key in out.keys():
                        target = key.upper()
                        if target in clean_dict and float(clean_dict[target]) != -9999.0:
                            out[key] = float(clean_dict[target])
            except Exception:
                pass
            return out

        year_metrics = parse_payload(url_year)
        norm_metrics = parse_payload(url_norm)
        st.session_state.last_raw_response = {"Year_Data": year_metrics, "Normal_Data": norm_metrics}
            
        row = pd.DataFrame([[
            spp, doy, yr, lat, lon, el, is_flowering, is_fruiting, is_vegetative,
            year_metrics["MAT"], year_metrics
