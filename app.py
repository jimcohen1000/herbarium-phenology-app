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

def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
            "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"
        ])
        df.to_csv(DB_FILE, index=False)

init_db()

col1, col2 = st.columns([1, 2])

if "form_data" not in st.session_state:
    st.session_state.form_data = None
if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

def extract_climate_var(data_dict, keys_to_try):
    if not isinstance(data_dict, dict):
        return None
    for key in keys_to_try:
        if key in data_dict:
            val = data_dict[key]
            try:
                if val is not None and float(val) != -9999.0:
                    return float(val)
            except ValueError:
                pass
        lower_dict = {k.lower(): v for k, v in data_dict.items()}
        if key.lower() in lower_dict:
            val = lower_dict[key.lower()]
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
        
        try:
            with st.spinner("Connecting to iNaturalist..."):
                inat_res = requests.get(inat_url, timeout=15).json()
            
            obs_list = inat_res.get("results", [])
            
            if not obs_list:
                st.warning("No research-grade observations found with phenology tags for this species.")
            else:
                new_rows = []
                progress_bar = st.progress(0)
                
                for idx, obs in enumerate
