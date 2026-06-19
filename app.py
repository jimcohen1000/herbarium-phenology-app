import streamlit as st
import pandas as pd
import plotly.express as px
import os
import requests
from datetime import date, datetime

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Full Ledger & Analytics")

db_file = "herbarium_database_expanded.csv"

# 1. INITIALIZE DATABASE WITH HEADERS
base_headers = [
    "Data_Source", "Collector", "Col_Number", "Barcode", "Species", "DOY", "Year",
    "Flowering", "Fruiting", "Vegetative", "Latitude", "Longitude", "Elevation", "URL"
]

if not os.path.exists(db_file):
    pd.DataFrame(columns=base_headers).to_csv(db_file, index=False)

# --- Helpers: API Fetchers ---
def get_elevation(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            elevations = res.json().get('elevation')
            if elevations and len(elevations) > 0:
                return float(elevations[0])
    except: 
        return None
    return None

def get_climate_data(lat, lon, el, prd):
    if el is None: return {} 
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

# Column 1: Data Collection
with c1:
    st.subheader("Data Collection")
    tab1, tab2 = st.tabs(["🌿 Herbarium", "🦋 iNaturalist"])
    
    # --- TAB 1: MANUAL HERBARIUM ENTRY ---
    with tab1:
        with st.form("data_entry_form"):
            collector = st.text_input("Collector Name")
            col_num = st.text_input("Collector Number")
            barcode = st.text_input("Barcode")
            spp = st.text_input("Species")
            
            date_val = st.date_input("Date", min_value=date(1900, 1, 1), max_value=date(2030, 12, 31), value=date(2020, 5, 1))
            
            st.write("**Phenology:**")
            col_f, col_fr, col_v = st.columns(3)
            with col_f: flow = st.checkbox("Flowering", value=True)
            with col_fr: fruit = st.checkbox("Fruiting")
            with col_v: veg = st.checkbox("Vegetative")
            
            lat = st.number_input("Lat", format="%.5f", value=51.1764)
            lon = st.number_input("Lon", format="%.5f", value=-115.5682)
            el = st.number_input("Elev (m)", value=1420)
            
            # PERFECTLY INDENTED SUBMIT BUTTON
            submitted = st.form_submit_button("💾 SAVE ENTRY", type="primary", use_container_width=True)
        
        if submitted:
            with st.spinner("Fetching climate models..."):
                year_data = get_climate_data(lat, lon, el, f"Year_{date_val.year}")
                norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
                
                row = {
                    "Data_Source": "Herbarium",
                    "Collector": collector, "Col_Number": col_num, "Barcode": barcode,
                    "Species": spp, "DOY": int(date_val.strftime("%j")), "Year": date_val.year,
                    "Flowering": flow, "Fruiting": fruit, "Vegetative": veg,
                    "Latitude": lat, "Longitude": lon, "Elevation": el, "URL": ""
                }
                
                for k, v in year_data.items(): row[f"Y_{k}"] = v
                for k, v in norm_data.items(): row[f"N_{k}"] = v
                
                df_existing = pd.read_csv(db_file)
                df_combined = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
                df_combined.to_csv(db_file, index=False)
                st.success("Herbarium Entry saved!")
                st.rerun()

    # --- TAB 2: INATURALIST BATCH IMPORT ---
    with tab2:
        with st.form("inat_import_form"):
            inat_spp = st.text_input("Target Species", "Anemone patens")
            inat_limit = st.slider("Records to Fetch", 5, 50, 25, step=5)
            st.info("Pulls Location -> Calculates Elevation -> Fetches ClimateNA models.")
            
            # PERFECTLY INDENTED SUBMIT BUTTON
            inat_submitted = st.form_submit_button("📥 FETCH & PROCESS DATA", type="primary", use_container_width=True)
            
        if inat_submitted:
            records = []
            url = f"https://api.inaturalist.org/v1/observations?taxon_name={inat_spp}&quality_grade=research&per_page={inat_limit}"
            
            st.write(f"Contacting iNaturalist for {inat_limit} records...")
            res = requests.get(url, timeout=15)
            
            if res.status_code == 200:
                data = res.json().get('results', [])
                if data:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, obs in enumerate(data):
                        if obs.get('location') and obs.get('observed_on'):
                            lat_str, lon_str = obs['location'].split(',')
                            date_str = obs['observed_on']
                            
                            try:
                                dt = datetime.strptime(date_str, "%Y-%m-%d")
                                lat, lon = float(lat_str), float(lon_str)
                                
                                status_text.text(f"Processing {i+1}/{len(data)}: Finding elevation...")
                                el = get_elevation(lat, lon)
                                
                                row = {
                                    "Data_Source": "iNaturalist",
                                    "Species": obs.get('taxon', {}).get('name', inat_spp),
                                    "Latitude": lat, "Longitude": lon, "Elevation": el,
                                    "Year": dt.year, "DOY": dt.timetuple().tm_yday,
                                    "URL": obs.get('uri', "")
                                }
                                
                                if el is not None:
                                    status_text.text(f"Processing {i+1}/{len(data)}: Pulling climate models...")
                                    year_data = get_climate_data(lat, lon, el, f"Year_{dt.year}")
                                    norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
                                    for k, v in year_data.items(): row[f"Y_{k}"] = v
                                    for k, v in norm_data.items(): row[f"N_{k}"] = v
                                
                                records.append(row)
                            except Exception:
                                pass
                        
                        progress_bar.progress((i + 1) / len(data))
                    
                    status_text.text("Finished processing!")
                    
                    if records:
                        df_existing = pd.read_csv(db_file)
                        df_combined = pd.concat([df_existing, pd.DataFrame(records)], ignore_index=True)
                        df_combined.to_csv(db_file, index=False)
                        st.success(f"Successfully added {len(records)} iNaturalist records!")
                        st.rerun()
                else:
                    st.warning("No records found for that species.")
            else:
                st.error("Failed to connect to iNaturalist.")

# Column 2: Graphing & Database
with c2:
    st.subheader("📊 Analysis Dashboard")
    
    # Read the data and ensure it doesn't crash if old columns are missing
    df = pd.read_csv(db_file)
    for col in base_headers:
        if col not in df.columns:
            df[col] = None
    
    # --- GRAPH SECTION ---
    if not df.empty and len(df) > 0:
        plot_vars = ["Year", "Latitude", "Longitude", "Elevation"] + [c for c in df.columns if c.startswith('Y_') or c.startswith('N_')]
        
        if len(plot_vars) > 0:
            g1, g2 = st.columns(2)
            with g1: x_var = st.selectbox("Select X-Axis Variable:", plot_vars)
            with g2: 
                species_list = df["Species"].dropna().unique()
                selected_spp = st.multiselect("Filter Species:", species_list, default=species_list)
            
            plot_df = df[df["Species"].isin(selected_spp)].copy()
            
            if x_var in plot_df.columns:
                plot_df[x_var] = pd.to_numeric(plot_df[x_var], errors='coerce')
                plot_df = plot_df.dropna(subset=[x_var, "DOY"])
                if not plot_df.empty:
                    fig = px.scatter(
                        plot_df, x=x_var, y="DOY", 
                        color="Data_Source", 
                        hover_data=["Year", "URL"] if "URL" in plot_df.columns else ["Year"],
                        trendline="ols", 
                        title=f"Phenology (DOY) vs {x_var} by Source"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Not enough valid data points to graph.")
    else:
        st.info("No data collected yet. Add your first entry on the left to see the graph!")
        
    st.write("---")
    
    # --- TABLE SECTION ---
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
            "Latitude": st.column_config.NumberColumn("Lat", format="%.4f"),
            "Longitude": st.column_config.NumberColumn("Lon", format="%.4f"),
            "Elevation": st.column_config.NumberColumn("Elev", format="%d m"),
            "URL": st.column_config.LinkColumn("Link"),
            "Data_Source": st.column_config.TextColumn("Source")
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
