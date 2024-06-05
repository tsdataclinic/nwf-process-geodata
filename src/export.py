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

class s3Exporter():

    def __init__(self):
        self.s3 = get_s3_client()
        self.bucket_name = "dataclinic-nwf"

    def export_all(self, local_download_dir):
        bucket_contents = self.s3.list_objects_v2(Bucket=self.bucket_name)

        if not os.path.exists(local_download_dir):
            os.makedirs(local_download_dir)

        for item in tqdm(bucket_contents['Contents']):
            file_name = item['Key']
            file_path = os.path.join(local_download_dir, file_name)

            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))

            self.s3.download_file(self.bucket_name, file_name, file_path)
            print(f"Downloaded {file_name} to {file_path}")

if __name__ == "__main__":
    s3Exporter().export_all("export_test")
