import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title("Herbarium Tracker: Climate Analysis Dashboard")

db_file = "herbarium_database_expanded.csv"

if not os.path.exists(db_file):
    st.info("Database is empty. Please add some entries from the data entry page first.")
    st.stop()

df = pd.read_csv(db_file)

# --- Analysis Dashboard ---
st.subheader("Interactive Phenology Plotter")

# 1. Identify climate variables (those starting with Y_ or N_)
climate_vars = [col for col in df.columns if col.startswith('Y_') or col.startswith('N_')]

col1, col2 = st.columns([1, 3])

with col1:
    st.write("### Graph Settings")
    x_var = st.selectbox("Select Climate Variable (X-Axis):", climate_vars)
    selected_spp = st.multiselect("Filter by Species:", df["Species"].unique(), default=df["Species"].unique())
    add_trendline = st.checkbox("Show Trendline", value=True)

with col2:
    # Filter data
    plot_df = df[df["Species"].isin(selected_spp)].copy()
    plot_df[x_var] = pd.to_numeric(plot_df[x_var], errors='coerce')
    plot_df = plot_df.dropna(subset=[x_var, "DOY"])

    if not plot_df.empty:
        trend = "ols" if add_trendline else None
        fig = px.scatter(
            plot_df, 
            x=x_var, 
            y="DOY", 
            color="Year",
            trendline=trend,
            hover_data=["Species", "Barcode", "Collector"],
            title=f"Relationship between {x_var} and Phenology (DOY)",
            labels={"DOY": "Day of Year", x_var: "Value from ClimateNA"},
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No data points available for the selected filters.")

st.write("---")
st.subheader("Raw Data View")
st.dataframe(df, use_container_width=True)
