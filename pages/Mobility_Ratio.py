import streamlit as st
import geopandas as gpd
import pydeck as pdk
import requests
from io import BytesIO
from shapely.geometry import Point  # Import Point from shapely.geometry

# Function to load GeoJSON data with new caching command
@st.cache_data
def load_data(url, state_name):
    response = requests.get(url)
    data = gpd.read_file(BytesIO(response.content))
    data = data[data['STATENAME'] == state_name]
    # Select only the desired columns
    columns_to_load = ['STATENAME', 'LEA_NAME', 'LCITY', 'MEMBER', 'STUTERATIO', 'District Name', 'Region', 'geometry', 'AVG(final Mobility Mean)']
    data = data[columns_to_load]
    return data

# Load the entire GeoJSON data from S3
url = 'https://s3-middle-public.s3.amazonaws.com/merged_geojson_attrition.geojson'
geo_data = load_data(url, "NORTH CAROLINA")

# Create an alias for the property name
alias = 'Mobility Mean'
geo_data = geo_data.rename(columns={'AVG(final Mobility Mean)': alias})

# Choose the property to base the color shading on
property_name = alias

# Ensure the property column exists
if property_name not in geo_data.columns:
    st.error(f"The property '{property_name}' is not found in the GeoDataFrame.")
    st.stop()

# Fill NaN values in the property column with 0 or another default value
geo_data[property_name] = geo_data[property_name].fillna(0.0)

# Function to map a property value to color (white to dark blue gradient)
def get_color(value, max_value):
    color_intensity = 255 - min(255, max(0, int(value / max_value * 255)))
    return [color_intensity, color_intensity, 255, 140]  # RGBA: white to dark blue with partial transparency

# Find the maximum value of the property for normalization
max_value = geo_data[property_name].max()

# Apply color mapping function
geo_data['fill_color'] = geo_data[property_name].apply(lambda x: get_color(x, max_value))

# Reproject to a projected CRS (e.g., EPSG:3857)
geo_data = geo_data.to_crs(epsg=3857)

# Calculate centroid coordinates in the projected CRS
centroid = geo_data.geometry.centroid
mean_latitude = centroid.y.mean()
mean_longitude = centroid.x.mean()

# Convert centroid to a Point and create a GeoDataFrame
centroid_point = Point(mean_longitude, mean_latitude)
centroid_geo = gpd.GeoDataFrame(index=[0], crs="EPSG:3857", geometry=[centroid_point])

# Reproject centroid to geographic CRS
centroid_geo = centroid_geo.to_crs(epsg=4326)
mean_latitude = centroid_geo.geometry.y[0]
mean_longitude = centroid_geo.geometry.x[0]

# Reproject geo_data back to geographic CRS for visualization
geo_data = geo_data.to_crs(epsg=4326)

# Streamlit app layout
st.title("GeoJSON Data Analytics Pydeck")

# Multiselect for tooltip fields
available_columns = geo_data.columns.tolist()
tooltip_fields = st.multiselect("Select fields for tooltip:", available_columns, default=['STATENAME', alias])

# Construct the tooltip HTML dynamically
tooltip_html = ""
for field in tooltip_fields:
    tooltip_html += f"<b>{field}:</b> {{{field}}}<br>"

tooltip = {
    "html": tooltip_html,
    "style": {
        "backgroundColor": "steelblue",
        "color": "white"
    }
}

# Pydeck visualization
layer = pdk.Layer(
    'GeoJsonLayer',
    geo_data.__geo_interface__,
    pickable=True,
    stroked=True,
    filled=True,
    extruded=False,
    wireframe=True,
    get_fill_color='[properties.fill_color[0], properties.fill_color[1], properties.fill_color[2], properties.fill_color[3]]',
    get_line_color=[255, 255, 255],  # Set line color to white for visibility
    line_width_min_pixels=0.5,  # Set minimum line width for reduced thickness
    highlight_color=[255, 255, 255, 150],  # Transparent white for highlighting
    auto_highlight=True  # Enable auto highlighting
)

# Custom CSS to set the size of the Pydeck map container
st.markdown(
    """
    <style>
    .deckgl-wrapper {
        width: 200%;
        height: 600px; /* Adjust the height as needed */
    }
    .legend {
        position: absolute;
        bottom: 10px;
        right: 10px;
        margin-bottom: 30px;
        background: white;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.5);
        z-index: 1000;
    }
    .legend div {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 5px;
        color: black;  /* Set text color to black */
    }
    .color-box {
        width: 20px;
        height: 20px;
        margin-right: 10px;
        border: 1px solid black;  /* Added border for outline */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Define initial view state for the map
view_state = pdk.ViewState(
    latitude=mean_latitude,
    longitude=mean_longitude,
    zoom=5,  # Adjust zoom level as needed
    pitch=0,
    bearing=0
)

# Display the Pydeck chart with fixed dimensions
st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

# Add a legend for the map shading inside the map
st.markdown("""
<div class="legend">
    <div><div class="color-box" style="background: rgba(255, 255, 255, 0.55);"></div>Low Mobility Ratio</div>
    <div><div class="color-box" style="background: rgba(128, 128, 255, 0.55);"></div>Medium Mobility Ratio</div>
    <div><div class="color-box" style="background: rgba(0, 0, 255, 0.55);"></div>High Mobility Ratio</div>
</div>
""", unsafe_allow_html=True)
