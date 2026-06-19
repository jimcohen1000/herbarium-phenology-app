import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.title("Herbarium Tracker - Reset")

# Flat data setup
headers = ["Species", "DOY", "Year", "Latitude", "Longitude", "MAT", "Data_Source"]
db_file = "herbarium_database_multi_source.csv"

# Safe simple init
if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# Super compact columns
c1, c2 = st.columns(2)

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    yr = st.number_input("Year Collected", 1900, 2026, 2020)
    doy = st.number_input("Day of Year (DOY)", 1, 365, 120)
    lat = st.number_input("Latitude", 40.0, 60.0, 51.176)
    lon = st.number_input("Longitude", -130.0, -60.0, -115.568)
    btn = st.button("Save Point")
    
    if btn:
        # Direct URL call with no hidden dictionary blocks
        q_yr = 2024 if yr > 2024 else yr
        url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el=1200&prd=Year_{q_yr}&varYSM=YSM"
        
        mat = "Data Unavailable"
        try:
            res = requests.get(url, timeout=10).json()
            data = res[0] if isinstance(res, list) else res
            if "MAT" in data and float(data["MAT"]) != -9999.0:
                mat = float(data["MAT"])
        except Exception:
            pass
            
        row = pd.DataFrame([[spp, doy, yr, lat, lon, mat, "Herbarium"]], columns=headers)
        row.to_csv(db_file, mode='a', header=False, index=False)
        st.success("Point saved successfully!")
        st.rerun()

with c2:
    st.subheader("Database & Visualizations")
    try:
        df = pd.read_csv(db_file)
    except Exception:
        df = pd.DataFrame(columns=headers)
        
    if df.empty:
        st.info("No records found yet.")
    else:
        st.dataframe(df, use_container_width=True)
        fig = px.scatter(df, x="MAT", y="DOY", color="Year", title="Phenology Trends")
        st.plotly_chart(fig, use_container_width=True)
