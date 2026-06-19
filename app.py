import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Phenology & Climate Change Tracker")

# Define the file name for our local database
DB_FILE = "herbarium_database.csv"

# Helper function to initialize CSV if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT"])
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
        
        # CHANGED: Replaced Dropdown menu with Checkboxes for multiple selections
        st.write("Phenology Stage (Select all that apply):")
        c_flowering = st.checkbox("Flowering")
        c_fruiting = st.checkbox("Fruiting")
        c_none = st.checkbox("None / Vegetative Only")
        
        lat = st.number_input("Latitude", format="%.5f", value=51.17641)
        lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
        el = st.number_input("Elevation (meters)", min_value=0, value=1420)
        
        submitted = st.form_submit_button("Grab ClimateNA Data & Plot")

    if submitted:
        # Process the checkboxes into a single clean string
        stages = []
        if c_flowering: stages.append("Flowering")
        if c_fruiting: stages.append("Fruiting")
        if c_none: stages.append("None")
        
        phenology_stage = ", ".join(stages) if stages else "Unspecified"

        if not species.strip():
            st.error("Please enter a plant species name.")
        elif collection_date.year < 1901:
            # Informative error check for ClimateNA historical limits
            st.error(f"ClimateNA does not contain historical data for the year {collection_date.year}. Please select a date from 1901 onward.")
        else:
            year = collection_date.year
            doy = int(collection_date.strftime("%j")) 
            
            # ClimateNA API Call endpoint
            api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?lat={lat}&lon={lon}&el={el}&prd={year}&varYSM=Y"
            
            try:
                with st.spinner("Fetching climate data from ClimateNA..."):
                    response = requests.get(api_url, timeout=10).json()
                    
                mat = response.get("MAT", None)
                
                if mat is not None:
                    new_data = pd.DataFrame([[species, doy, year, phenology_stage, lat, lon, el, mat]], 
                                            columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT"])
                    new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Added {species} ({phenology_stage})! Calculated DOY: {doy}. MAT: {mat}°C.")
                else:
                    # Improved guidance for the 'MAT' error
                    st.error("ClimateNA connected, but 'MAT' was missing. Note: ClimateNA only supports locations within North America and years from 1901-present.")
            except Exception as e:
                st.error("Failed to connect to ClimateNA. Please check your internet connection or coordinates.")

# 3. Interactive Graphing & Data Viewer (Right Column)
with col2:
    st.header("Analysis Dashboard")
    
    df = pd.read_csv(DB_FILE)
    
    if df.empty:
        st.info("The database is currently empty
