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

# IMPROVED EXTRACTOR: Case-insensitive fallback matching for precise key safety
def extract_climate_var(data_dict, key):
    if not isinstance(data_dict, dict):
        return None
        
    # Create a lowercase mapping of the entire dictionary to catch any case mismatches
    clean_dict = {str(k).lower().strip(): v for k, v in data_dict.items()}
    target_key = str(key).lower().strip()
    
    if target_key in clean_dict:
        val = clean_dict[target_key]
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
    
    inat_species = st.text_input("Species to Import from iNat", placeholder="e.g., Anemone patens", key="inat_spp_input")
    max_results = st.slider("Max observations to pull", 5, 50, 20, key="inat_slider")
    import_clicked = st.button("Fetch & Process iNat Data", key="inat_btn")
    
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
                    
                    mat_val, t_spring_val, t_summer_val, t_may_val = "Data Unavailable", "Data Unavailable", "Data Unavailable", "Data Unavailable"
                    api_url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1={idx}&ID2=test1&lat={lat}&lon={lon}&el={el}&prd=%20{query_year}&varYSM=YSM"
                    
                    cl_res = None
                    try:
                        cl_res = requests.get(api_url, timeout=7).json()
                        st.session_state.last_raw_response = cl_res
                    except Exception:
                        pass
                    
                    data_dict = {}
                    if isinstance(cl_res, list) and cl_res:
                        data_dict = cl_res[0]
                    elif isinstance(cl_res, dict):
                        data_dict = cl_res
                    
                    v_mat = extract_climate_var(data_dict, "MAT")
                    v_sp = extract_climate_var(data_dict, "Tave_sp")
                    v_sm = extract_climate_var(data_dict, "Tave_sm")
                    v_m5 = extract_climate_var(data_dict, "Tave_05")
                    
                    if v_mat is not None: mat_val = v_mat
                    if v_sp is not None: t_spring_val = v_sp
                    if v_sm is not None: t_summer_val = v_sm
                    if v_m5 is not None: t_may_val = v_m5
                    
                    new_rows.append([inat_species, doy, year, phenology_stage, lat, lon, el, mat_val, t_spring_val, t_summer_val, t_may_val, "iNaturalist"])
                    time.sleep(0.05)
                    progress_bar.progress((idx + 1) / total_items)
                
                if new_rows:
                    inat_df = pd.DataFrame(new_rows, columns=headers)
                    inat_df.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Successfully added {len(new_rows)} records!")

# ----------------- LEFT COLUMN: HERBARIUM MANUAL INPUT -----------------
with col1:
    st.header("Enter Herbarium Data")
    
    with st.form("herbarium_form", clear_on_submit=False):
        species = st.text_input("Plant Species", value="Anemone patens", key="manual_spp")
        collection_date = st.date_input("Collection Date", value=date(2020, 5, 1), key="manual_date")
        
        st.write("Phenology Stage:")
        c_flowering = st.checkbox("Flowering", value=True, key="chk_flow")
        c_fruiting = st.checkbox("Fruiting", key="chk_fruit")
        c_none = st.checkbox("None / Vegetative Only", key="chk_none")
        
        lat = st.number_input("Latitude", format="%.5f", value=51.17641, key="num_lat")
        lon = st.number_input("Longitude", format="%.5f", value=-115.56820, key="num_lon")
        el = st.number_input("Elevation (meters)", min_value=0, value=1420, key="num_el")
        
        submitted = st.form_submit_button("Submit Entry")

    if submitted:
        if not species.strip():
            st.error("Please enter a species name.")
        else:
            stages = []
            if c_flowering: stages.append("Flowering")
            if c_fruiting: stages.append("Fruiting")
            if c_none: stages.append("None")
            phenology_stage = ", ".join(stages) if stages else "Unspecified"
            
            year = collection_date.year
            doy = int(collection_date.strftime("%j"))
            
            query_year = 2024 if year > 2024 else year
            
            mat_val, t_spring_val, t_summer_val, t_may_val = "Data Unavailable", "Data Unavailable", "Data Unavailable", "Data Unavailable"
            api_url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=test1&lat={lat}&lon={lon}&el={el}&prd=%20{query_year}&varYSM=YSM"
            
            response = None
            try:
                response = requests.get(api_url, timeout=10)
            except Exception:
                pass
            
            if response is not None and response.status_code == 200:
                data_json = response.json()
                st.session_state.last_raw_response = data_json
                
                data_dict = {}
                if isinstance(data_json, list) and data_json:
                    data_dict = data_json[0]
                elif isinstance(data_json, dict):
                    data_dict = data_json
                
                v_mat = extract_climate_var(data_dict, "MAT")
                v_sp = extract_climate_var(data_dict, "Tave_sp")
                v_sm = extract_climate_var(data_dict, "Tave_sm")
                v_m5 = extract_climate_var(data_dict, "Tave_05")
                
                if v_mat is not None: mat_val = v_mat
                if v_sp is not None: t_spring_val = v_sp
                if v_sm is not None: t_summer_val = v_sm
                if v_m5 is not None: t_may_val = v_m5

            new_row = pd.DataFrame([[species, doy, year, phenology_stage, lat, lon, el, mat_val, t_spring_val, t_summer_val, t_may_val, "Herbarium"]], columns=headers)
            new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
            st.success("Entry added to database!")

# ----------------- RIGHT COLUMN: VISUALIZATIONS & FILTERS -----------------
with col2:
    st.header("Analysis Dashboard")
    
    # PERMANENT DIAGNOSTIC WINDOW: Always visible right at the top for real-time monitoring
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console", expanded=True):
            st.write("Below is the exact text map returned by the api.climatena.ca server:")
            st.json(st.session_state.last_raw_response)
    else:
        st.info("💡 Diagnostic Console: Submit data on the left or use the iNaturalist importer to view raw API parameters.")
            
    try:
        df = pd.read_csv(DB_FILE)
    except Exception:
        df = pd.DataFrame()
    
    if st.sidebar.button("⚠️ Clear All Records", key="clear_db_btn"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        pd.DataFrame(columns=headers).to_csv(DB_FILE, index=False)
        st.rerun()

    if not df.empty:
        st.subheader("Graph Settings")
        f1, f2, f3 = st.columns(3)
        with f1:
            x_axis_var = st.selectbox("Climate Metric:", ["MAT", "Tave_Spring", "Tave_Summer", "Tave_May"], index=1, key="sel_metric")
        with f2:
            all_spp = ["All Species"] + list(df["Species"].unique())
            sel_spp = st.selectbox("Species Filter:", all_spp, key="sel_spp_filter")
        with f3:
            sel_src = st.selectbox("Source Filter:", ["All Sources", "Herbarium Only", "iNaturalist Only"], key="sel_src_filter")

        plot_df = df.copy()
        for col in ["MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "DOY", "Year"]:
            plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce')
            
        if sel_spp != "All Species":
            plot_df = plot_df[plot_df["Species"] == sel_spp]
        if sel_src == "Herbarium Only":
            plot_df = plot_df[plot_df["Data_Source"] == "Herbarium"]
        elif sel_src == "iNaturalist Only":
            plot_df = plot_df[plot_df["Data_Source"] == "iNaturalist"]

        valid_df = plot_df.dropna(subset=[x_axis_var, "DOY", "Year"])
        
        if valid_df.empty:
            st.warning("No records found matching those parameters.")
        else:
            fig = px.scatter(
                valid_df, 
                x=x_axis_var, 
                y="DOY", 
                color="Year",
                symbol="Data_Source",
                hover_data=["Phenology_Stage", "Elevation"],
                size_max=12,
                title="Phenology Shift Trends",
                labels={"DOY": "Day of Year Collected", "Year": "Collection Year"},
                color_continuous_scale=px.colors.sequential.Plasma
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Live CSV Database View")
        st.dataframe(df, use_container_width=True)
