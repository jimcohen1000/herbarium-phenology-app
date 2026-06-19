if st.button("Save Entry", use_container_width=True):
        with st.spinner("Fetching climate models..."):
            # Fetch both datasets
            year_data = get_climate_data(lat, lon, el, f"Year_{date_val.year}")
            norm_data = get_climate_data(lat, lon, el, "Normal_1961_1990")
            
            # Build the base row
            row = {
                "Collector": collector, "Col_Number": col_num, "Barcode": barcode,
                "Species": spp, "DOY": int(date_val.strftime("%j")), "Year": date_val.year,
                "Flowering": flow, "Fruiting": fruit, "Vegetative": veg,
                "Latitude": lat, "Longitude": lon, "Elevation": el
            }
            
            # Append all climate data dynamically
            for k, v in year_data.items(): row[f"Y_{k}"] = v
            for k, v in norm_data.items(): row[f"N_{k}"] = v
            
            # Safely merge and save
            df_existing = pd.read_csv(db_file)
            df_new = pd.DataFrame([row])
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            
            df_combined.to_csv(db_file, index=False)
            st.success("Entry saved!")
            st.rerun()
