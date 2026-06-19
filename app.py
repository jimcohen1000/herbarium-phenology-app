import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

st.set_page_config(layout="wide")
st.title("Herbarium Phenology & Climate Change Tracker")

# Define the file name for our local database
DB_FILE = "herbarium_database_enriched.csv"

# Helper function to initialize CSV if it doesn't exist
def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
            "Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", 
            "MAT", "Tave_Spring", "Tave_Summer", "Tave_May"
        ])
        df.to_csv(DB_FILE, index=False)

init_db()

# Create two columns layout: Left for Form, Right for Visualizations
col1, col2 = st.columns([1, 2])

# We use session state flags to handle form submissions cleanly outside the form container
if "form_data" not in st.session_state:
    st.session_state.form_data = None

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

    # Capture form action inside the block, but don't process heavy states here
    if submitted:
        stages = []
        if c_flowering: stages.append("Flowering")
        if c_fruiting: stages.append("Fruiting")
        if c_none: stages.append("None")
        phenology_stage = ", ".join(stages) if stages else "Unspecified"

        if not species.strip():
            st.error("Please enter a plant species name.")
        else:
            st.session_state.form_data = {
                "species": species,
                "date": collection_date,
                "stage": phenology_stage,
                "lat": lat,
                "lon": lon,
                "el": el
            }

# CRITICAL FIX: Run data processing logic completely OUTSIDE the st.form block
if st.session_state.form_data is not None:
    data = st.session_state.form_data
    # Clear the temporary state trigger right away so it doesn't double-submit
    st.session_state.form_data = None 
    
    year = data["date"].year
    doy = int(data["date"].strftime("%j"))
    
    mat_val = "Data Unavailable"
    t_spring_val = "Data Unavailable"
    t_summer_val = "Data Unavailable"
    t_may_val = "Data Unavailable"
    
    if year >= 1901:
        # Aligned to official individual historical year API string notation ("Historical_YYYY")
        prd_string = f"Historical_{year}"
        api_base = "https://api6.climatebc.ca/api/clmApi6/LatLonEl"
        api_params = f"?ID1=1&ID2=test&lat={data['lat']}&lon={data['lon']}&el={data['el']}&prd={prd_string}&varYSM=YSM"
        api_url = api_base + api_params
        
        try:
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                data_json = response.json()
                data_dict = data_json[0] if isinstance(data_json, list) and data_json else data_json
                
                if isinstance(data_dict, dict):
                    v_mat = data_dict.get("MAT")
                    v_sp = data_dict.get("Tave_sp")
                    v_sm = data_dict.get("Tave_sm")
                    v_m5 = data_dict.get("Tave05")
                    
                    if v_mat is not None: mat_val = float(v_mat)
                    if v_sp is not None: t_spring_val = float(v_sp)
                    if v_sm is not None: t_summer_val = float(v_sm)
                    if v_m5 is not None: t_may_val = float(v_m5)
        except Exception:
            pass

    # Save rows cleanly into CSV
    new_row = pd.DataFrame([[data["species"], doy, year, data["stage"], data["lat"], data["lon"], data["el"], mat_val, t_spring_val, t_summer_val, t_may_val]], 
                            columns=["Species", "DOY", "Year", "Phenology_Stage", "Latitude", "Longitude", "Elevation", "MAT", "Tave_Spring", "Tave_Summer", "Tave_May"])
    new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
    st.rerun()

# 3. Interactive Graphing & Data Viewer (Right Column)
with col2:
    st.header("Analysis Dashboard")
    
    df = pd.read_csv(DB_FILE)
    
    df_plot_clean = df.copy()
    df_plot_clean["MAT"] = pd.to_numeric(df_plot_clean["MAT"], errors='coerce')
    df_plot_clean["Tave_Spring"] = pd.to_numeric(df_plot_clean["Tave_Spring"], errors='coerce')
    df_plot_clean["Tave_Summer"] = pd.to_numeric(df_plot_clean["Tave_Summer"], errors='coerce')
    df_plot_clean["Tave_May"] = pd.to_numeric(df_plot_clean["Tave_May"], errors='coerce')
    df_plot_clean["DOY"] = pd.to_numeric(df_plot_clean["DOY"], errors='coerce')
    df_plot_clean["Year"] = pd.to_numeric(df_plot_clean["Year"], errors='coerce')
        
    graph_df = df_plot_clean.dropna(subset=["DOY", "Year"])
    
    # Sidebar control to reset database if needed
    if st.sidebar.button("⚠️ Reset Database (Clear Rows)"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        st.rerun()

    if df.empty:
        st.info("The database is currently empty. Submit your first herbarium entry on the left!")
    else:
        st.subheader("Graph Configurations")
        x_axis_var = st.selectbox(
            "Select Climate Variable for X-Axis:",
            ["MAT", "Tave_Spring", "Tave_Summer", "Tave_May"],
            index=1
        )
        
        valid_graph_df = graph_df.dropna(subset=[x_axis_var])
        
        if valid_graph_df.empty:
            st.info("Data logged! Graphs will show up once a submission registers numerical variables.")
        else:
            all_species = ["All Species"] + list(valid_graph_df["Species"].unique())
            selected_species = st.selectbox("Filter Graph by Species:", all_species)
            
            plot_df = valid_graph_df if selected_species == "All Species" else valid_graph_df[valid_graph_df["Species"] == selected_species]
            
            labels_map = {
                "MAT": "Mean Annual Temp (°C)",
                "Tave_Spring": "Mean Spring Temp (°C)",
                "Tave_Summer": "Mean Summer Temp (°C)",
                "Tave_May": "Mean May Temp (°C)"
            }
            
            fig = px.scatter(
                plot_df, 
                x=x_axis_var, 
                y="DOY", 
                color="Year",
                hover_data=["Phenology_Stage"],
                size_max=12,
                title=f"Phenology Shift: Day of Year vs. {labels_map[x_axis_var]} ({selected_species})",
                labels={x_axis_var: labels_map[x_axis_var], "DOY": "Day of Year Collected", "Year": "Collection Year"},
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
