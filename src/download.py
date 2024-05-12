import pathlib
import geopandas as gpd
import pandas as pd
import boto3
import botocore
import json
import urllib.request
import os
from src.common import TARGET_CRS, get_s3_client, BUCKET_NAME
from tqdm import tqdm

import requests
from urllib.error import HTTPError


class DataDownloaderUploader:

    def __init__(self):
        self.s3 = get_s3_client()
        self.metadata_df = pd.read_csv("NWF_metadata.csv")

    def _exists_in_s3(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket="dataclinic-nwf", Key=key)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise
        return True
    
    def _download_to_local(self, url: str, path: str):
        """
        Retrieves a file from a specified URL and saves it locally.
        
        Parameters:
        - url: str, the URL from which the file will be downloaded.
        
        Returns:
        - str, the path to the locally saved file.
        """
        try:
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            if path.endswith(".geojson"):
                self._download_geojson(url, path)
            else:
                urllib.request.urlretrieve(url, path)
        except HTTPError as e:
            print(f"Failed to download {url} - {e}")
            return None
        return path
    
    def _download_geojson(self, url: str, path: str) -> None:
        offset = 0
        batch_sz = 1000
        downloaded = {"type": "FeatureCollection", "features": []}
        while True:
            response = requests.get(url.split("?")[0], params={"where": "1=1", "outFields": "*", "f": "geojson", "resultOffset": offset, "resultRecordCount": batch_sz})
            data = response.json()
            downloaded["features"].extend(data["features"])
            if len(data["features"]) < batch_sz:
                break
            offset += batch_sz
        with open(path, "w") as f:
            json.dump(downloaded, f)

    def _upload_to_s3(self, local_path: str, s3_path: str) -> None:
        """
        Uploads a file from a local directory to an Amazon S3 bucket.
        The local file should probably be deleted.
        
        Parameters:
        - local_path: str, the path to the file on the local file system.
        - s3_path: str, the target path in the S3 bucket where the file will be uploaded.
        """
        self.s3.upload_file(local_path, "dataclinic-nwf", s3_path)
        print(f"Successfully uploaded {s3_path}")
        pathlib.Path(local_path).unlink()

    def _create_path(self, metadata_row: pd.Series):
        """
        Constructs an S3 path for a file based on the metadata categories provided in a DataFrame row.
        
        Parameters:
        - metadata_row: Series, a row from the metadata DataFrame containing category information for path construction.
        
        Returns:
        - str, the constructed S3 path.
        """
        category: str | None = self._to_dir(metadata_row["New Category"])
        subtype: str | None = self._to_dir(metadata_row["Subtype"])
        individual: str | None = self._to_dir(metadata_row["Individual"])
        subdir: str | None = "/".join(["data", "raw", category, subtype, individual]) if category and subtype and individual else None
        if subdir:
            fmt: str = metadata_row["format"]
            ext: str | None = ".geojson" if fmt == "geojson" else ".zip" if fmt == "shapefile" else None
        return subdir + ext if subdir and ext else None

    def _to_dir(self, val):
        return val.strip().lower().replace(" ", "_").replace("/", "_") if not pd.isna(val) else None

    def download_and_upload_main(self, overwrite: bool = False) -> None:
        """
        Takes metadata dataframe and retreives content from "data_link" column
        to upload to s3 bucket.

        Files on s3 should be named according to metadata category hierarchy, e.g.,
        dataclinic-nwf/data/raw/wildlife/big_game_hunt_areas/antelope/antelope_hunt_areas.geojson

        Parameters:
        - metadata_df: DataFrame, contains the metadata which includes URLs to download and category hierarchy for S3 path generation.
        - overwrite: bool, if False, skips uploading files that already exist in the S3 bucket, avoiding overwriting.
        """
        for _, row in tqdm(self.metadata_df.iterrows()):
            download_url = row["data_link"]
            if pd.isna(download_url):
                continue
            path: str | None = self._create_path(row)
            if path:
                self.metadata_df.at[_, 's3_raw_path'] = path  
                if overwrite or not self._exists_in_s3(path):
                    local_path: str | None = self._download_to_local(download_url, path)
                    if local_path:
                        self._upload_to_s3(local_path, path)
        self.metadata_df.to_csv("output_metadata.csv")

if __name__ == "__main__":
    DataDownloaderUploader().download_and_upload_main()
