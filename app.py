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
                
                for idx, obs in enumerate(obs_list):
                    obs_date_str = obs.get("observed_on")
                    if not obs_date_str: continue
                    
                    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d")
                    year = obs_date.year
                    doy = int(obs_date.strftime("%j"))
                    
                    if year < 1901 or year > 2026: continue
                    
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
                    
                    mat_val = "Data Unavailable"
                    t_spring_val = "Data Unavailable"
                    t_summer_val = "Data Unavailable"
                    t_may_val = "Data Unavailable"
                    
                    base_url = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
                    query_params = f"?ID1={idx}&ID2=test1&lat={lat}&lon={lon}&el={el}&prd=%20{year}&varYSM=YSM"
                    api_url = base_url + query_params
                    
                    # CLEANED TRY BLOCK: Isolated strictly to the web request action
                    cl_res = None
                    try:
                        cl_res = requests.get(api_url, timeout=7).json()
                        st.session_state.last_raw_response = cl_res
                    except Exception:
                        pass
                    
                    # Unpack values safely outside the network try container block
                    data_dict = {}
                    if isinstance(cl_res, list) and cl_res:
                        data_dict = cl_res[0]
                    elif isinstance(cl_res, dict):
                        data_dict = cl_res
                    
                    v_mat = extract_climate_var(data_dict, ["MAT"])
                    v_sp = extract_climate_var(data_dict, ["Tave_sp"])
                    v_sm = extract_climate_var(data_dict, ["Tave_sm"])
                    v_m5 = extract_climate_var(data_dict, ["Tave05"])
                    
                    if v_mat is not None:
                        mat_val = v
