import pandas as pd
import geopandas as gpd
import re

# Load the CSV file
csv_df = pd.read_csv('only_attrition_mobility_table.csv')

# Filter out non-numeric District Numbers
csv_df = csv_df[csv_df['District Number'].apply(lambda x: str(x).isdigit())]

# Convert District Number to integer
csv_df['District Number'] = csv_df['District Number'].astype(int)

# Load the GeoJSON file
geojson_gdf = gpd.read_file('processed_data.geojson')

# Function to extract numeric part from ST_LEAID
def extract_numeric(value):
    match = re.search(r'\d+', value)
    return int(match.group()) if match else None

# Apply the function to the 'ST_LEAID' column in the GeoDataFrame
geojson_gdf['numeric_key'] = geojson_gdf['ST_LEAID'].apply(extract_numeric)

# Initialize the GeoJSON attributes with default values
geojson_gdf['District Name'] = ""
geojson_gdf['Region'] = ""
geojson_gdf['District Number'] = 0
geojson_gdf['SUM(final LEAAttrition Sum)'] = 0
geojson_gdf['SUM(final Mobility Sum)'] = 0
geojson_gdf['SUM(final StateAttrition N)'] = 0
geojson_gdf['SUM(final StateAttrition Sum)'] = 0
geojson_gdf['SUM(Recoup n)'] = 0
geojson_gdf['AVG(final LEAAttrition Mean)'] = 0.0
geojson_gdf['AVG(final Mobility Mean)'] = 0.0
geojson_gdf['AVG(final StateAttrition Mean)'] = 0.0
geojson_gdf['AVG(Recoup rate)'] = 0.0

# Create a dictionary from the CSV for quick lookup
csv_dict = csv_df.set_index('District Number').to_dict('index')

# Update GeoJSON with data from CSV
for idx, row in geojson_gdf.iterrows():
    district_number = row['numeric_key']
    if district_number in csv_dict:
        geojson_gdf.at[idx, 'District Number'] = district_number  # Ensure District Number is updated
        for column in csv_dict[district_number]:
            geojson_gdf.at[idx, column] = csv_dict[district_number][column]

# Drop the temporary 'numeric_key' column
geojson_gdf = geojson_gdf.drop(columns=['numeric_key'])

# Save the merged GeoDataFrame to a new GeoJSON file
geojson_gdf.to_file('merged_geojson_attrition.geojson', driver='GeoJSON')
