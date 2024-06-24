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

import requests
from urllib.error import HTTPError

class s3Exporter():

    def __init__(self, bucket_name=BUCKET_NAME, local_download_dir='export_test'):
        self.s3 = get_s3_client()
        self.bucket_name = bucket_name
        self.local_download_dir = local_download_dir

    def export_all(self):
        bucket_contents = self.s3.list_objects_v2(Bucket=self.bucket_name)

        if not os.path.exists(self.local_download_dir):
            os.makedirs(self.local_download_dir)

        for item in tqdm(bucket_contents['Contents']):
            file_name = item['Key']
            file_path = os.path.join(self.local_download_dir, file_name)

            if not os.path.exists(os.path.dirname(file_path)):
                os.makedirs(os.path.dirname(file_path))

            self.s3.download_file(self.bucket_name, file_name, file_path)
            print(f"Downloaded {file_name} to {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export all objects")
    parser.add_argument('--s3bucket', type=str, default=BUCKET_NAME,
                        help="The s3 bucket to use for the pipeline")
    parser.add_argument('--local-download-dir', type=str, default='export_local',
                        help="The local directory to export all data")
    inputs = parser.parse_args()

    s3e = s3Exporter(bucket_name=inputs.s3bucket, local_download_dir=inputs.local_download_dir)
    s3e.export_all()
