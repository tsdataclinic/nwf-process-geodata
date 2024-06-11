import pathlib
import geopandas as gpd
import pandas as pd
import boto3
import botocore
import json
import urllib.request
import os
from common import TARGET_CRS, get_s3_client, BUCKET_NAME
from tqdm import tqdm
from zipfile import ZipFile 
import requests
from urllib.error import HTTPError


class DataDownloaderUploader:

    def __init__(self, bucket_name=BUCKET_NAME, noupload=False, overwrite=False):
        self.s3 = get_s3_client()
        self.metadata_df = pd.read_csv("NWF_metadata.csv")
        self.noupload = noupload
        self.overwrite = overwrite

    def _exists_in_s3(self, key: str) -> bool:
        try:
            self.s3.head_object(Bucket="dataclinic-nwf", Key=key)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                raise
        return True

    def _extract_layer_from_zip(self, zip_path, layer_to_extract, output_dir):
        with ZipFile(zip_path, 'r') as z:
            file_list = z.namelist()
            for file in file_list:
                if file.endswith(layer_to_extract):
                    z.extract(file, path=output_dir)
                    return os.path.join(output_dir, file)
            raise ValueError(f"Layer {layer_to_extract} not found in {zip_path}")

    def _download_census_water(self, path):
        counties = ["001", "003", "005", "007", "009", "011", "013", "015", "017", "019", "021", "023", "025", "027", "029", "031", "033", "035", "037", "039", "041", "043", "045"]

        gdfs = []
        for county in counties:
            url = f"https://www2.census.gov/geo/tiger/TIGER2023/AREAWATER/tl_2023_56{county}_areawater.zip"
            gdf = gpd.read_file(url)
            gdfs.append(gdf)

        full_water = pd.concat(gdfs)
        full_water.to_file(path)

    def _download_to_local(self, url: str, path: str, layer_to_extract=None):
        try:
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            if url == "https://www2.census.gov/geo/tiger/TIGER2023/AREAWATER/":
                self._download_census_water(path)
            elif path.endswith(".geojson"):
                self._download_geojson(url, path)
            else:
                urllib.request.urlretrieve(url, path)
            if layer_to_extract:
                return self._extract_layer_from_zip(path, layer_to_extract, dir)
        except (HTTPError, ValueError) as e:
            print(f"Failed to download or extract {url} - {e}")
            return None
        return path

    def _download_geojson(self, url: str, path: str) -> None:
        offset = 0
        batch_sz = 1000
        if url.startswith("https://services1"):
            batch_sz = 2000
        downloaded = {"type": "FeatureCollection", "features": []}
        while True:
            response = requests.get(
                url.split("?")[0],
                params={
                    "where": "1=1",
                    "outFields": "*",
                    "f": "geojson",
                    "resultOffset": offset,
                    "resultRecordCount": batch_sz,
                },
            )
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
        if not self.noupload:
            self.s3.upload_file(local_path, self.bucket_name, s3_path)
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
        subdir: str | None = (
            # Use individual twice to have each file in its own directory.
            # This is useful for adding documentation to the same folder
            # in a downstream step.
            "/".join(["data", "raw", category, subtype, individual, individual])
            if category and subtype and individual
            else None
        )
        if subdir:
            fmt: str = metadata_row["format"]
            format_to_extension = {
                "geojson": ".geojson",
                "shapefile": ".zip",
                "gdb": ".zip",
                "tar.gz": ".tar.gz",
                "zipped img": ".img",
                "zipped tif": ".tif"
            }
            ext: str = format_to_extension.get(fmt)  # Returns None if fmt is not found
            # if subdir and ext: print(subdir + ext)

        return subdir + ext if subdir and ext else None

    def _to_dir(self, val):
        return (
            val.strip().lower().replace(" ", "_").replace("/", "_")
            if not pd.isna(val)
            else None
        )

    def download_and_upload_main(self) -> None:
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
            layer_to_extract = None
            if row["format"] == "zipped img" or row["format"] == "zipped tif":
                layer_to_extract = row["layer"]
            if pd.isna(download_url):
                continue
            path: str | None = self._create_path(row)
            if path:
                self.metadata_df.at[_, "s3_raw_path"] = path
                if self.overwrite or not self._exists_in_s3(path):
                    local_path: str | None = self._download_to_local(download_url, path, layer_to_extract)
                    if local_path and not self.noupload:
                        self._upload_to_s3(local_path, path)
                        print(f'Uploaded to {path}')
        self.metadata_df.to_csv("output_metadata.csv")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Download and upload data")
    parser.add_argument('--s3bucket', type=str, default=BUCKET_NAME,
                        help="The s3 bucket to use for the pipeline")
    parser.add_argument('--overwrite', action="store_true", default=False,
                        help="Overwrite data already processed")
    parser.add_argument('--noupload', action="store_true", default=False,
                        help="Skip uploading processed data to s3")
    inputs = parser.parse_args()

    ddu = DataDownloaderUploader(bucket_name=inputs.s3bucket,
                                 overwrite=inputs.overwrite,
                                 noupload=inputs.noupload)
    ddu.download_and_upload_main()
