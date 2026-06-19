import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Phenology & Climate Change Tracker")

# Define the file name for our local database
DB_FILE = "herbarium_database_enriched.csv"

# Helper function to initialize CSV if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
            "MAT", "Tave_Spring", "Tave_Summer", "Tave_May"
        ])
        df.to_csv(DB_FILE, index=False)

init_db()

# Create two columns layout: Left for Form, Right for Visualizations
col1, col2 = st.columns([1, 2])

with col1:
    st.header("Enter Herbarium Label Data")
    
    with st.form("herbarium_form"):
        species = st.text_input("Plant Species", placeholder="e.g., Anemone patens")
        
        collection_date = st.date_input(
            "Collection Date", 
            value=date(2000, 5, 1),
            min_value=date(1850, 1, 1),
            max_value=date(2050, 12, 31)
        )
        
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
            year = collection_date.year
            doy = int(collection_date.strftime("%j")) 
            
            # Default fallback text if API fails
            mat_val = "Data Unavailable"
            t_spring_val = "Data Unavailable"
            t_summer_val = "Data Unavailable"
            t_may_val = "Data Unavailable"
            
            if year >= 1901:
                prd_string = f"Year_{year}"
                api_base = "https://api6.climatebc.ca/api/clmApi6/LatLonEl"
                api_params = f"?ID1=1&ID2=test&lat={lat}&lon={lon}&el={el}&prd={prd_string}&varYSM=YSM"
                api_url = api_base + api_params
                
                try:
                    with st.spinner("Fetching climate data from ClimateNA..."):
                        response = requests.get(api_url, timeout=10)
                        
                    if response.status_code == 200:
                        data_json = response.json()
                        data_dict = data_json[0] if isinstance(data_json, list) and data_json else data_json
                        
                        if isinstance(data_dict, dict):
                            # Clean, line-by-line dictionary extraction
                            v_mat = data_dict.get("MAT")
                            v_sp = data_dict.get("Tave_sp")
                            v_sm = data_dict.get("Tave_sm")
                            v_m5 = data_dict.get("Tave05")
                            
                            if v_mat is not None: mat_val = float(v_mat)
                            if v_sp is not None: t_spring_val = float(v_sp)
                            if v_sm is not None: t_summer_val = float(v_sm)
                            if v_m5 is not None: t_may_val = float(v_m5)
                except Exception as e:
                    pass 
            
            # Write row to CSV file safely
            new_data = pd.DataFrame([[species, doy, year, phenology_stage, lat, lon, el, mat_val, t_spring_val, t_summer_val, t_may_val]], 
                                    columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT", "Tave_Spring", "Tave_Summer", "Tave_May"])
            new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
            
            if isinstance(mat_val, float):
                st.success(f"Added {species}! Captured Annual, Seasonal, and Monthly parameters.")
            else:
                st.warning(f"Added {species}, but ClimateNA variables were unavailable.")
            
            st.rerun()

# 3. Interactive Graphing & Data Viewer (Right Column)
with col2:
    st.header("Analysis Dashboard")
    
    df = pd.read_csv(DB_FILE)
    
    df_plot_clean = df.copy()
    df_plot_clean["MAT"] = pd.to_numeric(df_plot_clean["MAT"], errors='coerce')
    df_plot_clean["Tave_Spring"] = pd.to_numeric(df_plot_clean["Tave_Spring"], errors='coerce')
    df_plot_clean["Tave_Summer"] = pd.to_numeric(df_plot_clean["Tave_Summer"], errors='coerce')
    df_plot_clean["Tave_May"] = pd.to_numeric(df_plot_clean["Tave_May"], errors='coerce')
    df_plot_clean["DOY"] = pd.to_numeric(df_plot_clean["DOY"], errors='coerce')
    df_plot_clean["Year"] = pd.to_numeric(df_plot_clean["Year"], errors='coerce')
        
    graph_df = df_plot_clean.dropna(subset=["DOY", "Year"])
    
    # Sidebar control to reset database if needed
    if st.sidebar.button("⚠️ Reset Database (Clear Rows)"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        st
