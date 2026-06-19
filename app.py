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
        
        # CHANGED: Added min_value (1850) and max_value (2050) constraints to the date picker
        collection_date = st.date_input(
            "Collection Date", 
            value=date(2000, 5, 1),
            min_value=date(1850, 1, 1),
            max_value=date(2050, 12, 31)
        )
        
        phenology_stage = st.selectbox("Phenology Stage", ["Flowering", "Fruiting", "None"])
        
        lat = st.number_input("Latitude", format="%.5f", value=51.17641)
        lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
        el = st.number_input("Elevation (meters)", min_value=0, value=1420)
        
        submitted = st.form_submit_button("Grab ClimateNA Data & Plot")

    if submitted:
        if not species.strip():
            st.error("Please enter a plant species name.")
        else:
            year = collection_date.year
            doy = int(collection_date.strftime("%j")) 
            
            # ClimateNA API Call endpoint
            api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?lat={lat}&lon={lon}&el={el}&prd={year}&varYSM=Y"
            
            try:
                with st.spinner("Fetching climate data..."):
                    response = requests.get(api_url, timeout=10).json()
                    
                mat = response.get("MAT", None)
                
                if mat is not None:
                    new_data = pd.DataFrame([[species, doy, year, phenology_stage, lat, lon, el, mat]], 
                                            columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT"])
                    new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Added {species} ({phenology_stage})! Calculated DOY: {doy}. MAT: {mat}°C.")
                else:
                    st.error("ClimateNA data fetched, but 'MAT' was missing.")
            except Exception as e:
                st.error("Failed to connect to ClimateNA. Please check your coordinates.")

# 3. Interactive Graphing & Data Viewer (Right Column)
with col2:
    st.header("Analysis Dashboard")
    
    df = pd.read_csv(DB_FILE)
    
    if df.empty:
        st.info("The database is currently empty. Submit your first herbarium entry on the left to generate graphs!")
    else:
        all_species = ["All Species"] + list(df["Species"].unique())
        selected_species = st.selectbox("Filter Graph by Species:", all_species)
        
        plot_df = df if selected_species == "All Species" else df[df["Species"] == selected_species]
        
        fig = px.scatter(
            plot_df, 
            x="MAT",
