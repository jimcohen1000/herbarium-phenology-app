import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date
import time

st.set_page_config(layout="wide")
st.title("Herbarium & iNaturalist Phenology Tracker")

# Define the file name for our expanded database
DB_FILE = "herbarium_database_multi_source.csv"

# Helper function to initialize CSV if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
            "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"
        ])
        df.to_csv(DB_FILE, index=False)

init_db()

# Create two columns layout: Left for Form, Right for Visualizations
col1, col2 = st.columns([1, 2])

if "form_data" not in st.session_state:
    st.session_state.form_data = None
if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

# SMART PARSER: Matches document specs (handles case variants safely)
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
        # Fallback for lowercase conversions if the API shifts response formats
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
                    
                    # FIXED INDIVIDUAL LINES: Clean explicit string defaults split safely
                    mat_val = "Data Unavailable"
                    t_spring_val = "Data Unavailable"
                    t_summer_val = "Data Unavailable"
                    t_may_val = "Data Unavailable"
                    
                    # API Syntax targeting exact ClimateNA documentation
                    api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?ID1={idx}&ID2=iNat&lat={lat}&lon={lon}&el={el}&prd={year}&varYSM=YSM"
                    
                    try:
                        cl_res = requests.get(api_url, timeout=7).json()
                        st.session_state.last_raw_response = cl_res
                        data_dict = cl_res[0] if isinstance(cl_res, list) and cl_res else cl_res
                        
                        v_mat = extract_climate_var(data_dict, ["MAT"])
                        v_sp = extract_climate_var(data_dict, ["Tave_sp"])
                        v_sm = extract_climate_var(data_dict, ["Tave_sm"])
                        v_m5 = extract_climate_var(data_dict, ["Tave05"])
                        
                        if v_mat is not None: mat_val = v_mat
                        if v_sp is not None: t_spring_val = v_sp
                        if v_sm is not None: t_summer_val = v_sm
                        if v_m5 is not None: t_may_val = v_m5
                    except Exception:
                        pass
                    
                    new_rows.append([inat_species, doy, year, phenology_stage, lat, lon, el, mat_val, t_spring_val, t_summer_val, t_may_val, "iNaturalist"])
                    time.sleep(0.1)
                    progress_bar.progress((idx + 1) / len(obs_list))
                
                if new_rows:
                    inat_df = pd.DataFrame(new_rows, columns=[
                        "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
                        "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"
                    ])
                    inat_df.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Processed and merged {len(new_rows)} rows!")
                    st.rerun()
        except Exception as e:
            st.error(f"iNaturalist tracking failure: {str(e)}")

# ----------------- LEFT COLUMN: HERBARIUM MANUAL INPUT -----------------
with col1:
    st.header("Enter Herbarium Label Data")
    
    with st.form("herbarium_form"):
        species = st.text_input("Plant Species", placeholder="e.g., Anemone patens")
        collection_date = st.date_input("Collection Date", value=date(2000, 5, 1), min_value=date(1850, 1, 1), max_value=date(2050, 12, 31))
        
        st.write("Phenology Stage (Select all that apply):")
        c_flowering = st.checkbox("Flowering")
        c_fruiting = st.checkbox
