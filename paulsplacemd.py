#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium
from pyproj import Transformer

# Streamlit App Title
st.title("Homeless Shelter Locator Near Paul's Place")

# Hardcoded coordinates for Paul's Place
pauls_place_lat, pauls_place_lon = 39.2820504, -76.6328439

# API Endpoint
api_url = "https://services1.arcgis.com/UWYHeuuJISiGmgXx/arcgis/rest/services/Homeless_Shelter/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json"

# Coordinate Transformer (State Plane Maryland to WGS84)
transformer = Transformer.from_crs("EPSG:2248", "EPSG:4326", always_xy=True)

# Load CSV file with additional locations
@st.cache_data
def load_csv_data():
    try:
        csv_df = pd.read_csv("baltimore_help_social_health_welfare_shelters_locations.csv")  
        # Filter out Paul's Place from the CSV 
        csv_df = csv_df[csv_df["Location"] != "Paul's Place"]
        return csv_df
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        return pd.DataFrame()

# Fetch Data from API
@st.cache_data
def fetch_shelter_data():
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        features = data['features']
        shelters_data = [feature['attributes'] for feature in features]
        shelters_df = pd.DataFrame(shelters_data)
        return shelters_df
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching shelter data: {e}")
        return pd.DataFrame()

# Convert projected coordinates to latitude/longitude
def convert_coordinates(row):
    try:
        lon, lat = transformer.transform(row['x_coord'], row['y_coord'])
        return pd.Series([lat, lon])
    except Exception as e:
        st.warning(f"Error converting coordinates for shelter {row['name']}: {e}")
        return pd.Series([None, None])

# Main Function
def main():
    # Fetch shelter data
    shelters_df = fetch_shelter_data()

    # Load CSV data
    csv_df = load_csv_data()

    if not shelters_df.empty or not csv_df.empty:
        # Convert projected coordinates to latitude/longitude for API data
        if not shelters_df.empty:
            shelters_df[['latitude', 'longitude']] = shelters_df.apply(convert_coordinates, axis=1)
            shelters_df = shelters_df.dropna(subset=['latitude', 'longitude'])

        # Merge CSV data with API data
        if not csv_df.empty:
            # Rename columns in CSV data to match API data
            csv_df = csv_df.rename(columns={"Location": "name", "Latitude": "latitude", "Longitude": "longitude"})
            # Add missing columns to CSV data
            csv_df['address'] = "Not Available"  # Add a placeholder for missing address data
            csv_df['function'] = "Unknown"  # Default function for CSV data

            # Combine API and CSV data
            combined_df = pd.concat([shelters_df, csv_df], ignore_index=True)
        else:
            combined_df = shelters_df

        # Define a mapping of location names to their functions
          function_mapping = {
            "VOA Pratt House": "Emergency Shelters",
            "University of Maryland Medical Center": "Medical Services",
            "The Baltimore Station": "Emergency Shelters",
            "Christ Lutheran Place": "Emergency Shelters",
            "Grace Medical Center": "Medical Services",
            "American Rescue Workers": "Emergency Shelters",
            "ACC My Sister’s Place Lodge": "Emergency Shelters",
            "Seton Station": "Emergency Shelters",
            "Our Daily Bread": "Food & Meals",
            "Mercy Medical Center": "Medical Services",
            "Patrick Allison House": "Emergency Shelters",
            "Maryland Legal Aid": "Legal Services",
            "Interfaith ES": "Emergency Shelters",
            "Health Care for the Homeless": "Medical Services",
            "Weinberg Housing and Resource Center": "Emergency Shelters",
            "Maryland Center for Veterans Education and Training": "Veteran Services",
            "YWCA - Druid House": "Emergency Shelters",
            "ACC Christopher Place": "Emergency Shelters",
            "Chase Brexton Health Services": "Medical Services",
            "Code Blue J, H & R": "Emergency Shelters",
            "Helping Up Mission": "Emergency Shelters",
            "Salvation Army": "Emergency Shelters",
            "Karis House": "Emergency Shelters",
            "Baltimore Rescue Mission": "Emergency Shelters",
            "Aunt CC's Harbor House": "Emergency Shelters",
            "Earl’s Place": "Emergency Shelters",
            "Umar Boxing": "Community Services",
            "Pennsylvania Avenue Library": "Community Services",
            "Orleans Street Library": "Community Services",
            "SVdP Ozanam House": "Emergency Shelters",
            "Project PLASE": "Emergency Shelters",
            "East Baltimore Medical Center": "Medical Services",
            "Cherry Hill Library": "Community Services",
            "MedStar Harbor Hospital": "Medical Services",
            "Baltimore Safe Haven": "Emergency Shelters",
            "Johns Hopkins Hospital": "Medical Services",
            "Franciscan Center": "Food & Meals",
            "Kennedy Krieger Institute": "Medical Services",
            "Youth Empowered Society (YES)": "Youth Services",
            "ACC Project FRESH Start": "Emergency Shelters",
            "St. Vincent de Paul of Baltimore": "Emergency Shelters",
            "Northwest One-Stop Career Center": "Employment Services",
            "Church of the Guardian Angel": "Community Services",
            "At Jacob’s Well": "Emergency Shelters",
            "Prisoner’s Aid": "Legal Services",
            "Manna House": "Emergency Shelters",
            "Supportive Housing Group/Lanvale Institute": "Housing Services",
            "Collington Square": "Community Services",
            "Dayspring Village": "Housing Services",
            "J, H & R - VA": "Veteran Services",
            "J, H & R - Carrington House": "Veteran Services",
            "Sacred House": "Community Services",
            "Eastside One-Stop Career Center": "Employment Services",
            "Brooklyn Library": "Community Services",
            "Marian House": "Housing Services",
            "MedStar Union Memorial Hospital": "Medical Services",
            "SVdP Cottage Avenue": "Emergency Shelters",
            "Southeast Anchor Library": "Community Services",
            "Grace Baptist Church": "Community Services",
            "BMHS Ethel Elan Safe Haven II": "Emergency Shelters",
            "BMHS Safe Haven I": "Emergency Shelters",
            "Johns Hopkins Bayview Medical Center": "Medical Services",
            "Maryland Food Bank": "Food & Meals",
            "Park West Health System | Belvedere Ave.": "Medical Services",
            "Sinai Hospital": "Medical Services",
            "Levindale Hebrew Geriatric Center and Hospital": "Medical Services",
            "Mt. Washington Pediatric Hospital": "Medical Services",
            "MedStar Good Samaritan Hospital": "Medical Services",
            "Harbel Community Organization": "Community Services",
            
            }

        # Update the function column in the combined DataFrame
        combined_df['function'] = combined_df['name'].map(function_mapping).fillna("Unknown")

        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(combined_df['longitude'], combined_df['latitude'])]
        shelters_gdf = gpd.GeoDataFrame(combined_df, geometry=geometry, crs="EPSG:4326")

        # Filter within 10 miles
        def calculate_distance(row):
            return geodesic((pauls_place_lat, pauls_place_lon), (row['latitude'], row['longitude'])).miles

        # Calculate distances
        shelters_gdf['distance_to_pauls_place'] = shelters_gdf.apply(calculate_distance, axis=1)

        # Format distances as strings with "miles" appended
        shelters_gdf['distance_to_pauls_place'] = shelters_gdf['distance_to_pauls_place'].apply(lambda x: f"{x:.2f} miles")

        # Sort by distance in ascending order
        shelters_gdf_sorted = shelters_gdf.sort_values(by='distance_to_pauls_place', key=lambda x: x.str.replace(' miles', '').astype(float))

        # Display distances to Paul's Place in ascending order
        st.write("Distances to Paul's Place:")
        st.write(shelters_gdf_sorted[['name', 'function', 'distance_to_pauls_place']])

        # Filter shelters within 10 miles
        distance_threshold = 10  # 10 miles
        shelters_gdf_filtered = shelters_gdf_sorted[shelters_gdf_sorted['distance_to_pauls_place'].str.replace(' miles', '').astype(float) <= distance_threshold]

        # Allow users to filter by function/category
        function_options = shelters_gdf_filtered['function'].unique().tolist()
        selected_functions = st.multiselect("Filter by Function/Category:", function_options, default=function_options)

        # Filter by selected functions
        shelters_gdf_filtered = shelters_gdf_filtered[shelters_gdf_filtered['function'].isin(selected_functions)]

        # Print the filtered shelters within 10 miles
        st.write(f"Shelters Within {distance_threshold} Miles of Paul's Place:")
        st.dataframe(shelters_gdf_filtered[['name', 'function', 'address', 'distance_to_pauls_place']])

        # Folium Map
        m = folium.Map(location=[pauls_place_lat, pauls_place_lon], zoom_start=14)

        # Add Paul's Place as a purple marker
        folium.Marker(
            location=[pauls_place_lat, pauls_place_lon],
            popup="Paul's Place",
            icon=folium.Icon(color="purple", icon="info-sign")  # Pauls place purple marker with an info icon
        ).add_to(m)

        # Add shelters within 10 miles as green markers
        for idx, row in shelters_gdf_filtered.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"{row['name']} ({row['function']})",
                icon=folium.Icon(color="green")
            ).add_to(m)

        # Add a circle to show the 10-mile radius
        folium.Circle(
            location=[pauls_place_lat, pauls_place_lon],
            radius=distance_threshold * 1609.34,  # Convert miles to meters
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.2
        ).add_to(m)

        # Display the map in Streamlit
        st_folium(m, width=700, height=500)
    else:
        st.error("Shelter data could not be processed.")

if __name__ == "__main__":
    main()
