import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full Ledger & Analytics")

db_file = "herbarium_database_expanded.csv"

# 1. INITIALIZE DATABASE WITH HEADERS
base_headers = [
    "Collector", "Col_Number", "Barcode", "Species", "DOY", "Year",
    "Flowering", "Fruiting", "Vegetative", "Latitude", "Longitude", "Elevation"
]

if not os.path.exists(db_file):
    pd.DataFrame(columns=base_headers).to_csv(db_file, index=False)

# --- Helper: Climate Data Fetcher ---
def get_climate_data(lat, lon, el, prd):
    base = "https://api.climatena.ca/api/cnaApi6/LatLonEl"
    url = f"{base}?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd={prd}&varYSM=YSM"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return data[0] if isinstance(data, list) else data
    except: 
        return {}
    return {}

# --- Layout ---
c1, c2 = st.columns([1, 2.2])

# Column 1: Data Collection (NOW USING st.form)
with c1:
    st.subheader("Data Collection")
    
    # The form container groups everything together
    with st.form("data_entry_form"):
        collector = st.text_input("Collector Name")
        col_num = st.text_input("Collector Number")
        barcode = st.text_input("Barcode")
        spp = st.text_input("Species")
        
        date_val = st.date_input(
            "Date", 
            min_value=date(1900, 1, 1), 
            max_value=date(2030, 12, 31), 
            value=date(2020, 5, 1)
        )
        
        st.write("**Phenology:**")
        col_f, col_fr, col_v = st.columns(3)
        with col_f: flow = st.checkbox("Flowering", value=True)
        with col_fr: fruit = st.checkbox("Fruiting")
        with col_v: veg = st.checkbox("Vegetative")
        
        lat = st.number_input("Lat", format="%.5f", value=51.1764)
        lon = st.number_input("Lon", format="%.5f", value=-115.5682)
        el = st.number_input("Elev (m)", value=1420)
        
        # This button is explicitly locked to the form. type="primary" makes it brightly colored!
        submitted = st.form_submit_button("💾 SAVE ENTRY", type="primary", use_container_width=True)
    
    # What happens when the button is pressed
    if submitted:
        with st.spinner("Fetching climate models..."):
            year_data = get_climate_data(lat, lon, el, f"Year_{date_val.year}")
            norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
            
            row = {
                "Collector": collector, 
                "Col_Number": col_num, 
                "Barcode": barcode,
                "Species": spp, 
                "DOY": int(date_val.strftime("%j")), 
                "Year": date_val.year,
                "Flowering": flow, 
                "Fruiting": fruit, 
                "Vegetative": veg,
                "Latitude": lat, 
                "Longitude": lon, 
                "Elevation": el
            }
            
            for k, v in year_data.items(): 
                row[f"Y_{k}"] = v
            for k, v in norm_data.items(): 
                row[f"N_{k}"] = v
            
            df_existing = pd.read_csv(db_file)
            df_new = pd.DataFrame([row])
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            
            df_combined.to_csv(db_file, index=False)
            st.success("Entry saved!")
            st.rerun()

# Column 2: Graphing & Database
with c2:
    st.subheader("Analysis Dashboard")
    
    df = pd.read_csv(db_file)
    
    if not df.empty:
        climate_vars = [
            c for c in df.columns 
            if c.startswith('Y_') or c.startswith('N_')
        ]
        
        if len(climate_vars) > 0:
            g1, g2 = st.columns(2)
            with g1: 
                x_var = st.selectbox("Select Climate Variable:", climate_vars)
            with g2: 
                species_list = df["Species"].dropna().unique()
                selected_spp = st.multiselect(
                    "Filter Species:", 
                    species_list, 
                    default=species_list
                )
            
            plot_df = df[df["Species"].isin(selected_spp)].copy()
            
            if x_var in plot_df.columns:
                plot_df[x_var] = pd.to_numeric(plot_df[x_var], errors='coerce')
                plot_df = plot_df.dropna(subset=[x_var, "DOY"])
                if not plot_df.empty:
                    fig = px.scatter(
                        plot_df, 
                        x=x_var, 
                        y="DOY", 
                        color="Year", 
                        trendline="ols", 
                        title=f"DOY vs {x_var}"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Not enough valid data points to graph.")
        else:
            st.info("No climate variables (Y_ or N_) found to graph yet.")
    else:
        st.info("No data collected yet. Add your first entry on the left!")
        
    st.write("---")
    st.subheader("📋 Formatted Database Ledger")
    
    if not df.empty:
        df = df.sort_values(by=["Year", "DOY"], ascending=[False, False])
        
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Year": st.column_config.NumberColumn("Year", format="%d"),
            "DOY": st.column_config.NumberColumn("DOY"),
            "Flowering": st.column_config.CheckboxColumn("Flower"),
            "Fruiting": st.column_config.CheckboxColumn("Fruit"),
            "Vegetative": st.column_config.CheckboxColumn("Veg"),
            "Latitude": st.column_config.NumberColumn("Lat", format="%.4f"),
            "Longitude": st.column_config.NumberColumn("Lon", format="%.4f"),
        }
    )
    
    col_dl, _ = st.columns([1, 3])
    with col_dl:
        st.download_button(
            "📥 Download Full CSV", 
            data=df.to_csv(index=False), 
            file_name="full_data.csv", 
            use_container_width=True
        )
        
    with st.expander("⚠️ Danger Zone"):
        if st.button("Wipe Entire Database"):
            pd.DataFrame(columns=base_headers).to_csv(db_file, index=False)
            st.rerun()
