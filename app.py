import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date
import time

st.set_page_config(layout="wide")
st.title("Herbarium & iNaturalist Phenology Tracker")

DB_FILE = "herbarium_database_multi_source.csv"

# Safe database initialization
headers = [
    "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
    "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"
]
if not os.path.exists(DB_FILE):
    pd.DataFrame(columns=headers).to_csv(DB_FILE, index=False)
else:
    try:
        pd.read_csv(DB_FILE)
    except Exception:
        pd.DataFrame(columns=headers).to_csv(DB_FILE, index=False)

# Setup layout blocks safely at the top level
col1, col2 = st.columns([1, 2])

if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

def extract_climate_var(data_dict, key):
    if not isinstance(data_dict, dict):
        return None
    if key in data_dict:
        val = data_dict[key]
        try:
            if val is not None and float(val) != -9999.0:
                return float(val)
        except ValueError:
            pass
    return None

# ----------------- SIDEBAR: iNATURALIST BATCH IMPORTER -----------------
with st.sidebar:
    st.header("📥 iNaturalist Importer")
    st.write("Pull modern research-grade data down and link it seamlessly with ClimateNA.")
    
    inat_species = st.text_input("Species to Import from iNat", placeholder="e.g., Anemone patens")
    max_results = st.slider("Max observations to pull", 5, 50, 20)
    import_clicked = st.button("Fetch & Process iNat Data")
    
    if import_clicked and inat_species.strip():
        inat_url = f"https://api.inaturalist.org/v1/observations?species_name={inat_species}&quality_grade=research&term_id=1&per_page={max_results}"
        
        inat_res = None
        try:
            with st.spinner("Connecting to iNaturalist..."):
                inat_res = requests.get(inat_url, timeout=15).json()
        except Exception as e:
            st.error(f"Failed to connect to iNaturalist: {str(e)}")
            
        if inat_res is not None:
            obs_list = inat_res.get("results", [])
            if not obs_list:
                st.warning("No research-grade observations found.")
            else:
                new_rows = []
                progress_bar = st.progress(0)
                total_items = len(obs_list)
                
                for idx in range(total_items):
                    obs = obs_list[idx]
                    obs_date_str = obs.get("observed_on")
                    if not obs_date_str: continue
                    
                    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d")
                    year = obs_date.year
                    doy = int(obs_date.strftime("%j"))
                    
                    if year < 1901: continue
                    query_year = 2024 if year > 2024 else year
                    
                    location = obs.get("location")
                    if not location: continue
                    lat, lon = map(float, location.split(","))
                    
                    el = obs.get("elevation", None)
                    el = int(float(el)) if (el is not None and float(el) > 0) else 1200
                    
                    stages = []
                    annotations = obs.get("annotations", [])
                    for ann in annotations:
                        if ann.get("controlled_term_id") == 1:
                            val = ann.get("controlled_value_id")
                            if val == 2: stages.append("Flowering")
                            if val == 3: stages.append("Fruiting")
                    
                    phenology_stage = ", ".join(stages) if stages else "None"
