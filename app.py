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
        elif collection_date.year < 1901:
            st.error(f"ClimateNA does not contain historical data for the year {collection_date.year}. Please select a date from 1901 onward.")
        else:
            year = collection_date.year
            doy = int(collection_date.strftime("%j")) 
            
            # ClimateNA API Call endpoint (Added standard dummy ID parameters required by some versions of the API)
            api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?ID1=1&ID2=test&lat={lat}&lon={lon}&el={el}&prd={year}&varYSM=Y"
            
            try:
                with st.spinner("Fetching climate data from ClimateNA..."):
                    response = requests.get(api_url, timeout=10).json()
                
                # Unpack response
                data_dict = {}
                if isinstance(response, list) and len(response) > 0:
                    data_dict = response[0]
                elif isinstance(response, dict):
                    data_dict = response
                
                # Check for either 'MAT' or lowercase 'mat'
                mat = data_dict.get("MAT", data_dict.get("mat", None))
                
                if mat is not None:
                    mat_float = float(mat)
                    
                    new_data = pd.DataFrame([[species, doy, year, phenology_stage, lat, lon, el, mat_float]], 
                                            columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT"])
                    new_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                    st.success(f"Added {species} ({phenology_stage})! Calculated DOY: {doy}. MAT: {mat_float}°C.")
                else:
                    st.error("ClimateNA connected, but 'MAT' was missing.")
                    # DEBUG WINDOW: This shows us exactly what the API answered
                    st.warning("Diagnostic Mode — Raw API Response:")
                    st.write(response)
                    
            except Exception as e:
                st.error(f"Error processing data: {str(e)}.")
                if 'response' in locals():
                    st.write("Raw Response Context:", response)

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
        
        plot_df["MAT"] = pd.to_numeric(plot_df["MAT"], errors='coerce')
        plot_df["DOY"] = pd.to_numeric(plot_df["DOY"], errors='coerce')
        
        fig = px.scatter(
            plot_df, 
            x="MAT", 
            y="DOY", 
            color="Year",
            hover_data=["Phenology_Stage"],
            size_max=12,
            title=f"Phenology Shift: Day of Year vs. Mean Annual Temperature ({selected_species})",
            labels={"MAT": "Mean Annual Temp (°C)", "DOY": "Day of Year Collected", "Year": "Collection Year"},
            color_continuous_scale=px.colors.sequential.Plasma
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Live Enriched Database")
        
        with open(DB_FILE, "rb") as file:
            st.download_button(
                label="📥 Download Full Database (CSV)",
                data=file,
                file_name="herbarium_phenology_data.csv",
                mime="text/csv"
            )
            
        st.dataframe(df, use_container_width=True)
