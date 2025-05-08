import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def subset_country(country, path_to_health_master):
    """
    Creates subset df of health destinations in country from health master file

    Args:
        country (str): Country name (ADM0)
        path_to_health_master (str): path to Health.csv

    Returns:
        country_df (obj): subset of health.csv for specific country
    """
    df = pd.read_csv(path_to_health_master)
    country_df = df[df.Country==country]
    return country_df

def pd_to_gpd(df, output_path):
    """
    Convert pandas dataframe to geodataframe

    Args:
        df (obj): subset of health_df
    """
    geometry = [Point(xy) for xy in zip(df.Long, df.Lat)]
    gdf = gpd.GeoDataFrame(df, crs="EPSG:4326", geometry=geometry)
    gdf.to_file(output_path)
    
