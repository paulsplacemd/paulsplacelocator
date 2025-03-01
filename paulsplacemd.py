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

    if not shelters_df.empty:
        # Convert projected coordinates to latitude/longitude
        shelters_df[['latitude', 'longitude']] = shelters_df.apply(convert_coordinates, axis=1)

        # Drop rows with invalid coordinates
        shelters_df = shelters_df.dropna(subset=['latitude', 'longitude'])

        # Add a sample shelter near Paul's Place
        sample_shelter = {
            'name': 'Sample Shelter',
            'address': 'Near Paul\'s Place',
            'latitude': 39.2752,  # Latitude
            'longitude': -76.6329  # Longitude
        }
        # Convert the sample shelter to a DataFrame
        sample_shelter_df = pd.DataFrame([sample_shelter])
        # Append using pd.concat
        shelters_df = pd.concat([shelters_df, sample_shelter_df], ignore_index=True)

        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(shelters_df['longitude'], shelters_df['latitude'])]
        shelters_gdf = gpd.GeoDataFrame(shelters_df, geometry=geometry, crs="EPSG:4326")

        # Filter within 10 miles
        def calculate_distance(row):
            return geodesic((pauls_place_lat, pauls_place_lon), (row['latitude'], row['longitude'])).miles

        # Calculate distances
        shelters_gdf['distance_to_pauls_place'] = shelters_gdf.apply(calculate_distance, axis=1)

        # Format distances as strings with "miles" appended
        shelters_gdf['distance_to_pauls_place'] = shelters_gdf['distance_to_pauls_place'].apply(lambda x: f"{x:.2f} miles")

        # Display distances to Paul's Place
        st.write("Distances to Paul's Place:")
        st.write(shelters_gdf[['name', 'distance_to_pauls_place']].head())

        # Filter shelters within 10 miles
        distance_threshold = 10  # 10 miles
        shelters_gdf_filtered = shelters_gdf[shelters_gdf['distance_to_pauls_place'].str.replace(' miles', '').astype(float) <= distance_threshold]

        # Print the filtered shelters within 10 miles
        st.write(f"Shelters Within {distance_threshold} Miles of Paul's Place:")
        st.dataframe(shelters_gdf_filtered[['name', 'address', 'distance_to_pauls_place']])

        # Folium Map
        m = folium.Map(location=[pauls_place_lat, pauls_place_lon], zoom_start=14)

        # Add Paul's Place as a purple marker
        folium.Marker(
            location=[pauls_place_lat, pauls_place_lon],
            popup="Paul's Place",
            icon=folium.Icon(color="purple", icon="info-sign")  # Purple marker with an info icon
        ).add_to(m)

        # Add shelters within 10 miles as green markers
        for idx, row in shelters_gdf_filtered.iterrows():
            # Skip Paul's Place if it appears in the shelters data
            if row['latitude'] == pauls_place_lat and row['longitude'] == pauls_place_lon:
                continue
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=row['name'],
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
