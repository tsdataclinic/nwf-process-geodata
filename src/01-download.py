import geopandas as gpd
import pandas as pd
import boto3


def download_and_upload_main(metadata_df, overwrite = False):
    """
    Takes metadata dataframe and retreives content from 'data_link' column
    to upload to s3 bucket.

    Files on s3 should be named according to metadata category hierarchy, e.g.,
    dataclinic-nwf/data/raw/wildlife/big_game_hunt_areas/antelope/antelope_hunt_areas.geojson

    Parameters:
    - metadata_df: DataFrame, contains the metadata which includes URLs to download and category hierarchy for S3 path generation.
    - overwrite: bool, if False, skips uploading files that already exist in the S3 bucket, avoiding overwriting.
    """

    
def download_to_local(url):
    """
    Retrieves a file from a specified URL and saves it locally.
    
    Parameters:
    - url: str, the URL from which the file will be downloaded.
    
    Returns:
    - str, the path to the locally saved file.
    """
    # Implement download logic
    pass

def upload_to_s3(local_path, s3_path):
    """
    Uploads a file from a local directory to an Amazon S3 bucket.
    
    Parameters:
    - local_path: str, the path to the file on the local file system.
    - s3_path: str, the target path in the S3 bucket where the file will be uploaded.
    """
    # Implement upload logic
    pass

def create_path(metadata_row):
    """
    Constructs an S3 path for a file based on the metadata categories provided in a DataFrame row.
    
    Parameters:
    - metadata_row: Series, a row from the metadata DataFrame containing category information for path construction.
    
    Returns:
    - str, the constructed S3 path.
    """
    # Implement path creation logic based on metadata categories
    pass

if __name__ == '__main__':

    metadata_df = pd.read_csv('NWF_metadata.csv')
    download_and_upload_main(metadata_df, overwrite=False)