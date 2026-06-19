import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker - Stable Ledger")

headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", 
    "MAT_Year", "Tave_WT_Year", "Tave_SP_Year", "Tave_SM_Year", "Tave_05_Year",
    "MAT_Normal", "Tave_WT_Normal", "Tave_SP_Normal", "Tave_SM_Normal", "Tave_05_Normal",
    "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# Sidebar: Controls
with st.sidebar:
    st.header("⚙️ Controls")
    if os.path.exists(db_file):
        df_view = pd.read_csv(db_file)
        st.metric("Records", len(df_view))
        if len(df_view) > 0:
            st.download_button("📥 Download CSV", data=df_view.to_csv(index=False), file_name="data.csv")
    
    if st.button("⚠️ Wipe Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.rerun()

# Entry Form
c1, c2 = st.columns([1, 1.4])
with c1:
    spp = st.text_input("Species", "Anemone patens")
    date_val = st.date_input("Date", value=date(2020, 5, 1))
    yr, doy = date_val.year, int(date_val.strftime("%j"))
    
    flow = st.checkbox("Flowering")
    fruit = st.checkbox("Fruiting")
    veg = st.checkbox("Vegetative")
    
    lat = st.number_input("Lat", format="%.5f", value=51.17641)
    lon = st.number_input("Lon", format="%.5f", value=-115.56820)
    el = st.number_input("Elev (m)", value=1420)
    
    if st.button("Save Entry"):
        q_yr = 2024 if yr > 2024 else (1901 if yr < 1901 else yr)
        base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
        u_yr = base + f"?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{q_yr}.ann&varYSM=YSM"
        u_nm = base + f"?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=YSM"
        
        def get_data(u):
            try:
                res = requests.get(u, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    d = data[0] if isinstance(data, list) else data
                    # SAFELY parse numbers, ignoring invalid/non-numeric strings
                    out = {}
                    for k, v in d.items():
                        try:
                            val = float(v)
                            out[k.upper()] = val if val != -9999.0 else None
                        except (ValueError, TypeError):
                            out[k.upper()] = None
                    return out
            except Exception:
                pass
            return {}

        y_m = get_data(u_yr)
        n_m = get_data(u_nm)
        
        row = [spp, doy, yr, lat, lon, el, flow, fruit, veg,
               y_m.get("MAT"), y_m.get("TAVE_WT"), y_m.get("TAVE_SP"), y_m.get("TAVE_SM"), y_m.get("TAVE_05"),
               n_m.get("MAT"), n_m.get("TAVE_WT"), n_m.get("TAVE_SP"), n_m.get("TAVE_SM"), n_m.get("TAVE_05"),
               "Herbarium"]
        
        pd.DataFrame([row], columns=headers).to_csv(db_file, mode='a', header=False, index=False)
        st.success("Entry saved!")
        st.rerun()

# Dashboard
with c2:
    st.subheader("Data")
    df = pd.read_csv(db_file)
    if not df.empty:
        var = st.selectbox("X-Axis", [c for c in headers if "MAT" in c or "Tave" in c])
        # Force numeric conversion for plotting
        df[var] = pd.to_numeric(df[var], errors='coerce')
        fig = px.scatter(df.dropna(subset=[var, "DOY"]), x=var, y="DOY", color="Year", trendline="ols")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df)
