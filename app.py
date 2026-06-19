import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.title("Herbarium Phenology & Climate Change Tracker")

# 1. Data Entry Form
with st.form("herbarium_form"):
    species = st.text_input("Plant Species")
    doy = st.number_input("Day of Year (1-365)", min_value=1, max_value=365)
    year = st.number_input("Collection Year", min_value=1901, max_value=2024)
    lat = st.number_input("Latitude", format="%.5f")
    lon = st.number_input("Longitude", format="%.5f")
    el = st.number_input("Elevation (meters)", min_value=0)
    submitted = st.form_submit_submit_button("Submit Record")

# 2. ClimateNA API Call (Triggered on Submit)
if submitted:
    # Example API endpoint structure for ClimateNA
    api_url = f"https://api6.climatebc.ca/api/clmApi6/LatLonEl?lat={lat}&lon={lon}&el={el}&prd={year}&varYSM=Y"
    
    try:
        response = requests.get(api_url).json()
        # Extract variables like Mean Annual Temp (MAT) or DD>5 (Growing degree days)
        mat = response.get("MAT") 
        
        # Save to a local database/CSV (Appends new row)
        save_data(species, doy, year, lat, lon, el, mat)
        st.success("Record added and Climate data grabbed successfully!")
    except:
        st.error("Failed to fetch data from ClimateNA. Check coordinates.")

# 3. Interactive Graphing
if st.checkbox("Show Phenology Graphs"):
    df = pd.read_csv("herbarium_database.csv") # Read all collected data
    
    # Plotting Day of Year vs Mean Annual Temperature
    fig = px.scatter(df, x="MAT", y="doy", color="Year", 
                     title="Shift in Flowering Day of Year vs. Climate Temperature",
                     labels={"MAT": "Mean Annual Temp (°C)", "doy": "Day of Year Collected"})
    st.plotly_chart(fig)
