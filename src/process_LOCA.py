import pandas as pd
import boto3
import pandas as pd
import tarfile
import io
import os
os.chdir("/Users/canyonfoot/Documents/python_proj/nwf-process-geodata")
from src.common import *
from rasterio.mask import mask
from rasterio.io import MemoryFile
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.transform import from_origin
import numpy as np
from scipy.interpolate import griddata

def _read_LOCA_csv_from_s3_tar_gz(s3, bucket_name, tar_gz_key, skiprows=1):
    obj = s3.get_object(Bucket=bucket_name, Key=tar_gz_key)
    tar_gz_stream = io.BytesIO(obj['Body'].read())
    
    with tarfile.open(fileobj=tar_gz_stream, mode='r:gz') as tar:
        csv_files = [member for member in tar.getmembers() if member.isfile() and member.name.endswith('.csv')]
        
        if len(csv_files) == 0:
            raise ValueError(f"No CSV file found in the tar.gz archive: {tar_gz_key}")
        elif len(csv_files) > 1:
            raise ValueError(f"Multiple CSV files found in the tar.gz archive: {tar_gz_key}")
        
        csv_file = tar.extractfile(csv_files[0])
        df = pd.read_csv(csv_file, skiprows=skiprows)
    
    return df


def _preprocess_LOCA(df):
    value_col = "combined"
    df['LON'] = pd.to_numeric(df['LON'], errors='coerce')
    df['LAT'] = pd.to_numeric(df['LAT'], errors='coerce')
    df['1976-2005'] = pd.to_numeric(df['1976-2005'], errors='coerce')
    df['2016-2045.1'] = pd.to_numeric(df['2016-2045.1'], errors='coerce')

    df = df.replace(-999.0, np.NaN)
    df["combined"] = df["1976-2005"] + df["2016-2045.1"]

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.LON, df.LAT), crs='EPSG:4326')[[value_col, "geometry"]]

    return gdf

def _create_raster(gdf, full_path, value_col = 'combined', x_res = 0.05, y_res = 0.05):
    x_min, y_min, x_max, y_max = gdf.total_bounds

    # Create a transform
    transform = from_origin(x_min, y_max, x_res, y_res)

    # Prepare grid coordinates (correcting for typical meshgrid usage in scientific plotting)
    grid_y, grid_x = np.mgrid[y_max:y_min:-y_res, x_min:x_max:x_res]  # Notice the reversed order and negative step for y

    # Perform interpolation
    raster = griddata(
        points=(gdf.geometry.x, gdf.geometry.y),
        values=gdf[value_col], 
        xi=(grid_x, grid_y),
        method='nearest'
    )

    # Write the raster
    with rasterio.open(
        full_path, 
        'w',
        driver='GTiff',
        height=raster.shape[0],
        width=raster.shape[1],
        count=1,
        dtype=str(raster.dtype),
        crs='+proj=latlong',
        transform=transform,
    ) as dst:
        dst.write(raster, 1)
    
def _trim_raster_to_wy(raster_path, trim_path):
    # Read the raster file
    with rasterio.open(raster_path) as src:
        wyoming_gdf = gpd.read_file("wyoming.geojson")
        
        # Mask the raster with the polygon
        out_image, out_transform = mask(src, wyoming_gdf.geometry, crop=True)
        out_image[out_image == 0] = np.nan

        # Update metadata for the cropped raster
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata" : np.nan
        })
        
    with rasterio.open(trim_path, 'w', **out_meta) as dest:
        dest.write(out_image)

def main_process_LOCA(s3, BUCKET_NAME, tar_gz_key, full_path, trimmed_path):
    df = _read_LOCA_csv_from_s3_tar_gz(s3, BUCKET_NAME, tar_gz_key, skiprows=1)
    gdf = _preprocess_LOCA(df)
    _create_raster(gdf,full_path)
    _trim_raster_to_wy(full_path, trimmed_path)