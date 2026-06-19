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

# Helper function to initialize CSV if it doesn't exist (Updated with Data_Source)
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

# ----------------- SIDEBAR: iNATURALIST BATCH IMPORTER -----------------
with st.sidebar:
    st.header("📥 iNaturalist Importer")
    st.write("Automatically pull modern research-grade data into your database.")
    
    inat_species = st.text_input("Species to Import from iNat", placeholder="e.g., Anemone patens")
    max_results = st.slider("Max observations to pull", 5, 50, 20)
    import_clicked = st.button("Fetch & Process iNat Data")
    
    if import_clicked and inat_species.strip():
        # iNaturalist API endpoint for research-grade observations with annotations
        # term_id=1 means "Plant Phenology"
        inat_url = f"https://api.inaturalist.org/v1/observations?species_name={inat_species}&quality_grade=research&term_id=1&per_page={max_results}"
        
        try:
            with st.spinner("Querying iNaturalist..."):
                inat_res = requests.get(inat_url, timeout=15).json()
            
            obs_list = inat_res.get("results", [])
            
            if not obs_list:
                st.warning("No research-grade phenology observations found for this species.")
            else:
                new_rows = []
                progress_bar = st.progress(0)
                
                for idx, obs in enumerate(obs_list):
                    # Extract date details
                    obs_date_str = obs.get("observed_on") # YYYY-MM-DD
                    if not obs_date_str: continue
                    
                    obs_date = datetime.strptime(obs_date_str, "%Y-%m-%d")
                    year = obs_date.year
                    doy = int(obs_date.strftime("%j"))
                    
                    if year < 1901: continue
                    
                    # Extract Location
                    location = obs.get("location") # "lat,lon" string
                    if not location: continue
                    lat, lon = map(float, location.split(","))
                    
                    # Extract Elevation (default to 0 if missing)
                    el = obs.get("elevation", 0)
                    if el is None: el = 0
                    
                    # Determine Coded Phenology Stage from iNat Annotations
                    # value=2 is Flowering, value=3 is Fruiting
                    stages = []
                    annotations = obs.get("annotations", [])
                    for ann in annotations:
                        if ann.get("controlled_term_id") == 1:
                            val = ann.get("controlled_value_id")
                            if val == 2: stages.append("Flowering")
                            if val == 3: stages.append("Fruiting")
                    
                    phenology_stage = ", ".join(stages) if stages else "None"
                    
                    # Fetch ClimateNA Data sequentially
                    mat_val, t_spring_val, t_summer_val, t_may_val = "Data Unavailable", "Data Unavailable", "Data Unavailable", "Data Unavailable"
                    prd_string = f"Historical_{year}"
                    api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?ID1=1&ID2=test&lat={lat}&lon={lon}&el={el}&prd={prd_string}&varYSM=YSM"
                    
                    try:
                        cl_res = requests.get(api_url, timeout=5).json()
                        data_dict = cl_res[0] if isinstance(cl_res, list) and cl_res else cl_res
                        if isinstance(data_dict, dict):
                            v_mat = data_dict.get("MAT")
                            v_sp = data_dict.get("Tave_sp")
                            v_sm = data_dict.get("Tave_sm")
                            v_m5 = data_dict.get("Tave05")
                            
                            if v_mat is not None and float(v_mat) != -9999.0: mat_val = float(v_mat)
                            if v_sp is not None and float(v_sp) != -9999.0: t_spring_val = float(v_sp)
                            if v_sm is not None and float(v_sm) != -9999.0: t_summer_val = float(v_sm)
                            if v_m5 is not None and float(v_m5) != -9999.0: t_may_val = float(v_m5)
                    except Exception:
                        pass
                    
                    # Create the row structure tagged as iNaturalist
                    new_rows.append([inat_species, doy, year, phenology_stage, lat, lon, el, mat_val, t_spring_val, t_summer_val, t_may_val, "iNaturalist"])
                    
                    # Minor sleep to avoid hammer-spamming ClimateNA API limits
                    time.sleep(0.2)
                    progress_bar.progress((idx + 1) / len(obs_list))
                
                if new_rows:
                    inat_df = pd.DataFrame(new_rows, columns=[
                        "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
                        "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"
                    ])
                    inat_df.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Successfully processed and merged {len(new_rows)} rows from iNaturalist!")
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
        c_fruiting = st.checkbox("Fruiting")
        c_none = st.checkbox("None / Vegetative Only")
        
        lat = st.number_input("Latitude", format="%.5f", value=51.17641)
        lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
        el = st.number_input("Elevation (meters)", min_value=0, value=1420)
        
        submitted = st.form_submit_button("Grab ClimateNA Data & Plot")

    if submitted:
        stages = []
        if c_flowering: stages.append("Flowering")
        if c_fruiting: stages.append("Fruiting")
        if c_none: stages.append("None")
        phenology_stage = ", ".join(stages) if stages else "Unspecified"

        if not species.strip():
            st.error("Please enter a plant species name.")
        else:
            st.session_state.form_data = {
                "species": species, "date": collection_date, "stage": phenology_stage,
                "lat": lat, "lon": lon, "el": el
            }

if st.session_state.form_data is not None:
    data = st.session_state.form_data
    st.session_state.form_data = None 
    year = data["date"].year
    doy = int(data["date"].strftime("%j"))
    
    mat_val, t_spring_val, t_summer_val, t_may_val = "Data Unavailable", "Data Unavailable", "Data Unavailable", "Data Unavailable"
    
    if year >= 1901:
        prd_string = f"Historical_{year}"
        api_base = "https://api6.climatebc.ca/api/clmApi6/LatLonEl"
        api_params = f"?ID1=1&ID2=test&lat={data['lat']}&lon={data['lon']}&el={data['el']}&prd={prd_string}&varYSM=YSM"
        api_url = api_base + api_params
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data_json = response.json()
                data_dict = data_json[0] if isinstance(data_json, list) and data_json else data_json
                if isinstance(data_dict, dict):
                    v_mat = data_dict.get("MAT")
                    v_sp = data_dict.get("Tave_sp")
                    v_sm = data_dict.get("Tave_sm")
                    v_m5 = data_dict.get("Tave05")
                    
                    if v_mat is not None and float(v_mat) != -9999.0: mat_val = float(v_mat)
                    if v_sp is not None and float(v_sp) != -9999.0: t_spring_val = float(v_sp)
                    if v_sm is not None and float(v_sm) != -9999.0: t_summer_val = float(v_sm)
                    if v_m5 is not None and float(v_m5) != -9999.0: t_may_val = float(v_m5)
        except Exception:
            pass

    # Save manually entered row as "Herbarium"
    new_row = pd.DataFrame([[data["species"], doy, year, data["stage"], data["lat"], data["lon"], data["el"], mat_val, t_spring_val, t_summer_val, t_may_val, "Herbarium"]], 
                            columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "Data_Source"])
    new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
    st.rerun()

# ----------------- RIGHT COLUMN: VISUALIZATIONS & FILTERS -----------------
with col2:
    st.header("Analysis Dashboard")
    
    df = pd.read_csv(DB_FILE)
    
    df_plot_clean = df.copy()
    for col in ["MAT", "Tave_Spring", "Tave_Summer", "Tave_May", "DOY", "Year"]:
        df_plot_clean[col] = pd.to_numeric(df_plot_clean[col], errors='coerce')
        
    graph_df = df_plot_clean.dropna(subset=["DOY", "Year"])
    
    if st.sidebar.button("⚠️ Reset Database (Clear Rows)"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        init_db()
        st.rerun()

    if df.empty:
        st.info("The database is currently empty. Submit herbarium data or use the iNaturalist importer!")
    else:
        st.subheader("Graph Configurations")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            x_axis_var = st.selectbox("Select Climate Variable:", ["MAT", "Tave_Spring", "Tave_Summer", "Tave_May"], index=1)
        with f_col2:
            all_species = ["All Species"] + list(graph_df["Species"].unique())
            selected_species = st.selectbox("Filter by Species:", all_species)
        with f_col3:
            # NEW FILTER: Allow filtering chart items by Data Source (Herbarium, iNaturalist, or Both)
            source_options = ["All Sources", "Herbarium Only", "iNaturalist Only"]
            selected_source = st.selectbox("Filter by Data Source:", source_options)

        st.write("Filter Graph by Phenology Stage:")
        p_cols = st.columns(3)
        with p_cols[0]: f_flowering = st.checkbox("Show Flowering Data", value=True)
        with p_cols[1]: f_fruiting = st.checkbox("Show Fruiting Data", value=True)
        with p_cols[2]: f_none = st.checkbox("Show None / Vegetative Data", value=True)
        
        # Apply Filters
        plot_df = graph_df if selected_species == "All Species" else graph_df[graph_df["Species"] == selected_species]
        
        if selected_source == "Herbarium Only":
            plot_df = plot_df[plot_df["Data_Source"] == "Herbarium"]
        elif selected_source == "iNaturalist Only":
            plot_df = plot_df[plot_df["Data_Source"] == "iNaturalist"]

        allowed_stages = []
        if f_flowering: allowed_stages.append("Flowering")
        if f_fruiting: allowed_stages.append("Fruiting")
        if f_none: allowed_stages.append("None")
        
        if not allowed_stages:
            st.warning("All phenology stages unchecked.")
            plot_df = pd.DataFrame(columns=plot_df.columns)
        else:
            plot_df = plot_df[plot_df["Phenology_Stage"].apply(lambda x: any(stage in str(x) for stage in allowed_stages))]
        
        valid_graph_df = plot_df.dropna(subset=[x_axis_var])
        
        if valid_graph_df.empty:
            st.info("No matching records found with valid climate data.")
        else:
            labels_map = {"MAT": "Mean Annual Temp", "Tave_Spring": "Mean Spring Temp", "Tave_Summer": "Mean Summer Temp", "Tave_May": "Mean May Temp"}
            
            # CHANGED: The scatter plot map symbols are now split by 'Data_Source' (Circle vs Diamond)
            fig = px.scatter(
                valid_graph_df, x=x_axis_var, y="DOY", color="Year",
                symbol="Data_Source",
                hover_data=["Phenology_Stage", "Data_Source"],
                size_max=12,
                title=f"Phenology Shift vs {labels_map[x_axis_var]}",
                labels={x_axis_var: f"{labels_map[x_axis_var]} (°C)", "DOY": "Day of Year Collected", "Year": "Year"},
                color_continuous_scale=px.colors.sequential.Plasma
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Live Enriched Database")
        with open(DB_FILE, "rb") as file:
            st.download_button(label="📥 Download Full Database (CSV)", data=file, file_name="phenology_combined_data.csv", mime="text/csv")
        st.dataframe(df, use_container_width=True)
