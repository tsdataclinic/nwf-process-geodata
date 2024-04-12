import geopandas as gpd
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

def process_raw_datasets(overwrite=False):
    """
    Walks through 'data/raw' directory on 'dataclinic-nwf' bucket and performs processing steps 
    to output files while preserving the directory structure from the raw directory.
    
    Parameters:
    - overwrite: bool, if False, files that are already on the bucket are not replaced.
    """

def intersect_with_wyoming_boundaries(gdf, wyoming_gdf):
    """
    Intersects the GeoDataFrame with Wyoming boundaries to trim excess areas.
    
    Parameters:
    - gdf: GeoDataFrame, the dataset to be trimmed
    - wyoming_gdf: GeoDataFrame, boundaries of Wyoming

    Returns:
    - GeoDataFrame, the trimmed dataframe
    """
    # Implement intersection logic
    pass

def reproject(gdf, output_crs=4362):
    """
    Reprojects a GeoDataFrame to a specified coordinate reference system.
    
    Parameters:
    - gdf: GeoDataFrame, the dataset to reproject
    - output_crs: int, EPSG code for the target CRS

    Returns:
    - GeoDataFrame, the reprojected dataframe
    """
    # Implement reprojection logic
    pass

def write_processed(gdf, raw_path, format="geojson"):
    """
    Writes the processed GeoDataFrame to the correct location on the S3 bucket.
    
    Parameters:
    - gdf: GeoDataFrame, the processed dataset
    - raw_path: str, original path of the raw file
    - format: str, file format for output, default is 'geojson'
    """
    # Determine the output path based on raw_path
    # Write gdf to S3 at the calculated path
    pass

if __name__ == '__main__':

    process_raw_datasets(overwrite=False)