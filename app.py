import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Tracker - Custom Analytics & Filters")

# Database structural setup
headers = [
    "Species", "DOY", "Year", "Latitude", "Longitude", "Elevation",
    "Flowering", "Fruiting", "Vegetative", "MAT_Year", "MAT_Normal", "Data_Source"
]
db_file = "herbarium_database_multi_source.csv"

if "last_raw_response" not in st.session_state:
    st.session_state.last_raw_response = None

# Safe database initialization
if not os.path.exists(db_file):
    pd.DataFrame(columns=headers).to_csv(db_file, index=False)
else:
    try:
        test_df = pd.read_csv(db_file)
        if len(test_df.columns) != len(headers):
            pd.DataFrame(columns=headers).to_csv(db_file, index=False)
    except Exception:
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)

# ----------------- SIDEBAR CONTROLS (DOWNLOAD & RESET) -----------------
with st.sidebar:
    st.header("⚙️ Database Controls")
    
    try:
        current_df = pd.read_csv(db_file)
        row_count = len(current_df)
    except Exception:
        current_df = pd.DataFrame(columns=headers)
        row_count = 0
        
    st.metric(label="Total Records Stored", value=row_count)
    
    if row_count > 0:
        csv_data = current_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Database (CSV)",
            data=csv_data,
            file_name="herbarium_phenology_data.csv",
            mime="text/csv"
        )
    else:
        st.button("📥 Download Database (CSV)", disabled=True)
        
    st.write("---")
    
    # 1. RESET FILE CONTROLLER: Completely flushes rows and clears cached diagnostics
    if st.button("⚠️ Wipe & Reset Database"):
        pd.DataFrame(columns=headers).to_csv(db_file, index=False)
        st.session_state.last_raw_response = None
        st.success("Database table completely cleared!")
        st.rerun()

# ----------------- MAIN LAYOUT COLUMNS -----------------
c1, c2 = st.columns([1, 1.4])

with c1:
    st.subheader("Manual Data Entry")
    spp = st.text_input("Species Name", "Anemone patens")
    
    chosen_date = st.date_input("Collection Date", value=date(2020, 5, 1))
    yr = chosen_date.year
    doy = int(chosen_date.strftime("%j"))
    
    st.info(f"📅 DOY: **{doy}** | Year: **{yr}**")
    
    st.write("**Phenology Status (Select all that apply):**")
    is_flowering = st.checkbox("Flowering", value=True)
    is_fruiting = st.checkbox("Fruiting", value=False)
    is_vegetative = st.checkbox("None (Vegetative Only)", value=False)
    
    lat = st.number_input("Latitude", format="%.5f", value=51.17641)
    lon = st.number_input("Longitude", format="%.5f", value=-115.56820)
    el = st.number_input("Elevation (meters)", min_value=0, value=1420)
    
    btn = st.button("Save & Link Climate Data")
    
    if btn:
        q_yr = 2024 if yr > 2024 else (1901 if yr < 1901 else yr)
        
        # FIXED: Added .ann back specifically to the target year URL query structure
        url_year = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t1&lat={lat}&lon={lon}&el={el}&prd=Year_{q_yr}.ann&varYSM=YSM"
        url_norm = f"https://api.climatena.ca/api/cnaApi6/LatLonEl?ID1=1&ID2=t2&lat={lat}&lon={lon}&el={el}&prd=Normal_1961_1990&varYSM=YSM"
        
        mat_year = "Data Unavailable"
        mat_norm = "Data Unavailable"
        diagnostic_log = {}

        try:
            res_yr = requests.get(url_year, timeout=10)
            if res_yr.status_code == 200:
                data_yr = res_yr.json()
                diagnostic_log["Year_API_Raw"] = data_yr
                dict_yr = data_yr[0] if isinstance(data_yr, list) else data_yr
                if "MAT" in dict_yr and float(dict_yr["MAT"]) != -9999.0:
                    mat_year = float(dict_yr["MAT"])
        except Exception as e:
            diagnostic_log["Year_API_Exception"] = str(e)

        try:
            res_nm = requests.get(url_norm, timeout=10)
            if res_nm.status_code == 200:
                data_nm = res_nm.json()
                diagnostic_log["Normal_API_Raw"] = data_nm
                dict_nm = data_nm[0] if isinstance(data_nm, list) else data_nm
                if "MAT" in dict_nm and float(dict_nm["MAT"]) != -9999.0:
                    mat_norm = float(dict_nm["MAT"])
        except Exception as e:
            diagnostic_log["Normal_API_Exception"] = str(e)
            
        st.session_state.last_raw_response = diagnostic_log
            
        row = pd.DataFrame([[
            spp, doy, yr, lat, lon, el,
            is_flowering, is_fruiting, is_vegetative,
            mat_year, mat_norm, "Herbarium"
        ]], columns=headers)
        
        row.to_csv(db_file, mode='a', header=False, index=False)
        st.success("Data points successfully generated!")
        st.rerun()

with c2:
    st.subheader("Analysis Dashboard")
    
    if st.session_state.last_raw_response is not None:
        with st.expander("🔍 Live ClimateNA Diagnostic Console"):
            st.json(st.session_state.last_raw_response)
        
    try:
        df = pd.read_csv(db_file)
    except Exception:
        df = pd.DataFrame(columns=headers)
        
    if df.empty:
        st.info("The database is currently empty. Submit a data entry on the left to initialize the analysis models.")
    else:
        # 2. DYNAMIC CHART GRAPH FILTER INTERFACES
        st.write("---")
        st.subheader("Graph Configurations")
        
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            # Axis metric selector tool
            x_var = st.selectbox(
                "Select Climate Variable (X-Axis):", 
                ["MAT_Year", "MAT_Normal"], 
                format_func=lambda x: "Collection Year Mean Temp (MAT_Year)" if x == "MAT_Year" else "Baseline Normal Temp (MAT_Normal)"
            )
        with f_col2:
            # Species selector tracking tool
            distinct_species = ["All Species"] + list(df["Species"].unique())
            selected_spp = st.selectbox("Filter by Species:", distinct_species)
        with f_col3:
            # Phenology status selector tags
            st.write("**Filter Graph Status:**")
            show_flowering = st.checkbox("Show Flowering Data", value=True)
            show_fruiting = st.checkbox("Show Fruiting Data", value=True)
            
        # Parse datasets iteratively based on parameters selected above
        plot_df = df.copy()
        
        # Enforce numeric conversion on selected climate variable to prevent plotting errors
        plot_df[x_var] = pd.to_numeric(plot_df[x_var], errors='coerce')
        plot_df = plot_df.dropna(subset=[x_var, "DOY"])
        
        # Filter by Species if a specific one is selected
        if selected_spp != "All Species":
            plot_df = plot_df[plot_df["Species"] == selected_spp]
            
        # Filter by Phenology status checkboxes
        if not show_flowering:
            plot_df = plot_df[plot_df["Flowering"] != True]
        if not show_fruiting:
            plot_df = plot_df[plot_df["Fruiting"] != True]
            
        if plot_df.empty:
            st.warning("No data points match the selected filters.")
        else:
            # Render interactive visualization chart
            fig = px.scatter(
                plot_df, 
                x=x_var, 
                y="DOY", 
                color="Year",
                hover_data=["Species", "Latitude", "Longitude", "Elevation", "Flowering", "Fruiting"],
                title=f"Day of Year (DOY) vs {x_var}",
                labels={"DOY": "Day of Year Collected", x_var: f"{x_var} (°C)"},
                color_continuous_scale=px.colors.sequential.Plasma
            )
            st.plotly_chart(fig, use_container_width=True)
            
        st.write("---")
        st.subheader("Live Enriched Database View")
        st.dataframe(df, use_container_width=True)
