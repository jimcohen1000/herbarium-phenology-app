import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

st.title("Herbarium Tracker - Diagnostics")

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
    yr = st.number_input("Year Collected", 1901, 2026, 2020)
    doy = st.number_input("Day of Year (DOY)", 1, 365, 120)
    lat = st.number_input("Latitude", 40.0, 60.0, 51.176)
    lon = st.number_input("Longitude", -130.0, -60.0, -115.568)
    el = st.number_input("Elevation (meters)", min_value=0, value=1420) # Dynamic elevation input
    btn = st.button("Save Point")
    
    if btn:
        # FIXED: Using your precise Normal baseline string format and dynamic elevation variable
        url = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=%20Normal_1961_1990.nrm&varYSM=YSM"
        
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
        st.success("Point evaluated!")
        st.rerun()

with c2:
    st.subheader("Diagnostics & Database")
    
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console", expanded=True):
            st.write("This is exactly what the server responded with:")
            st.json(st.session_state.last_raw_response)
    else:
        st.info("💡 Submit a test coordinate to see the live server communication logs here.")
        
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
