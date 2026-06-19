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
            
            # Default fallback values if API fails
            mat_val = "Data Unavailable"
            t_spring_val = "Data Unavailable"
            t_summer_val = "Data Unavailable"
            t_may_val = "Data Unavailable"
            
            if year >= 1901:
                prd_string = f"Year_{year}"
                
                # FIXED: URL broken into explicit text chunks to bypass string wrapping issues completely
                api_base = "https://api6.climatebc.ca/api/clmApi6/LatLonEl"
                api_params = f"?ID1=1&ID2=test&lat={lat}&lon={lon}&el={el}&prd={prd_string}&varYSM=YSM"
                api_url = api_base + api_params
                
                try:
                    with st.spinner("Fetching climate data from ClimateNA..."):
                        response = requests.get(api_url, timeout=10)
                        
                        if response.status_code == 200:
                            data_json = response.json()
                            
                            data_dict = {}
                            if isinstance(data_json, list) and len(data_json) > 0:
                                data_dict = data_json[0]
                            elif isinstance(data_json, dict):
                                data_dict = data_json
                            
                            mat = data_dict.get("MAT", None)
                            t_spring = data_dict.get("Tave_sp", None) 
                            t_summer = data_dict.get("Tave_sm", None) 
                            t
