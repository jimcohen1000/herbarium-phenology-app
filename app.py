import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.title("Herbarium Tracker - Dynamic Climate Sync")

# Flat data setup
headers = ["Species", "DOY", "Year", "Latitude", "Longitude", "MAT", "Data_Source"]
db_file = "herbarium_database_multi_source.csv"

if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# Super compact columns
c1, c2 = st.columns(2)

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    
    # 1. CALCULATE DAY OF YEAR: Replaced numeric year with a proper Calendar Picker
    chosen_date = st.date_input("Collection Date", value=date(2020, 5, 1))
    
    # Extract structural date parts automatically
    yr = chosen_date.year
    doy = int(chosen_date.strftime("%j")) # Converts date directly to Day of Year (1-366)
    
    # Display the calculated day to the user for clarity
    st.info(f"📅 Calculated Day of Year (DOY): **{doy}** | Year: **{yr}**")
    
    lat = st.number_input("Latitude", format="%.5f", value=51.17641)
    lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
    el = st.number_input("Elevation (meters)", min_value=0, value=1420)
    btn = st.button("Save & Link Climate Data")
    
    if btn:
        # Cap the historical lookup bounds safely based on available ClimateNA datasets
        q_yr = 2024 if yr > 2024 else (1901 if yr < 1901 else yr)
        
        # 2. DYNAMIC ANNUAL YEAR QUERY: Swaps out the hardcoded normal string for Year_XXXX.ann
        url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=%20Year_{q_yr}.ann&varYSM=YSM"
        
        mat = "Data Unavailable"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                try:
                    st.session_state.last_raw_response = res.json()
                    data = st.session_state.last_raw_response
                    
                    data_dict = data[0] if isinstance(data, list) else data
                    if "MAT" in data_dict and float(data_dict["MAT"]) != -9999.0:
                        mat = float(data_dict["MAT"])
                except Exception:
                    st.session_state.last_raw_response = {"Raw Text": res.text}
            else:
                st.session_state.last_raw_response = {"Error Code": res.status_code, "Message": res.text}
        except Exception as e:
            st.session_state.last_raw_response = {"Connection Error": str(e)}
            
        row = pd.DataFrame([[spp, doy, yr, lat, lon, mat, "Herbarium"]], columns=headers)
        row.to_csv(db_file, mode='a', header=False, index=False)
        st.success(f"Point registered for annual record: {q_yr}!")
        st.rerun()

with c2:
    st.subheader("Diagnostics & Database")
    
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console", expanded=True):
            st.write("This is exactly what the server responded with:")
            st.json(st.session_state.last_raw_response)
    else:
        st.info("💡 Submit a calendar data point on the left to review the annual payload matrix.")
        
    try:
        df = pd.read_csv(db_file)
    except Exception:
        df = pd.DataFrame(columns=headers)
        
    if df.empty:
        st.info("No records found yet.")
    else:
        st.dataframe(df, use_container_width=True)
        valid_df = df[df["MAT"] != "Data Unavailable"]
        if not valid_df.empty:
            fig = px.scatter(valid_df, x="MAT", y="DOY", color="Year", title="Phenology Trends")
            st.plotly_chart(fig, use_container_width=True)
