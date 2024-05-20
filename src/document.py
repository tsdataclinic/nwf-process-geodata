
import pathlib
import geopandas as gpd
import pandas as pd
import boto3
import botocore
import json
import urllib.request
import os
from src.common import TARGET_CRS, get_s3_client, BUCKET_NAME

import requests
from urllib.error import HTTPError

from fpdf import FPDF


class DataDocumenter:

    def __init__(self) -> None:
        self.s3 = get_s3_client()
        self.metadata = pd.read_csv("./output_metadata.csv")

    def document_processed_data(self) -> None:
        resp = self.s3.list_objects_v2(Bucket=BUCKET_NAME)
        for item in resp.get('Contents', []):
            path = item['Key']
            if path.startswith('data/processed') and not path.endswith('.pdf'):
                resp = self.s3.get_object(Bucket=BUCKET_NAME, Key=path)
                self._write_to_pdf(path, resp['Body'])

    def _write_to_pdf(self, path, resp_body) -> None:
        row = self.metadata[self.metadata['s3_raw_path'].replace('.zip', '.geojson') == path.replace('processed', 'raw')]
        if row.empty:
            print(f'Could not find metadata for {path}')
            return
        data = json.loads(resp_body.read().decode('utf-8'))
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=12, style='B')
        pdf.cell(200, 10, txt=f"{row['data_title'].values[0]}", ln=True, align='C')
        pdf.set_font('Arial', size=10)
        pdf.cell(200, 10, txt=f"Summary: {row['data_summary'].values[0]}", ln=True)
        pdf.cell(200, 10, txt=f'Path: {path}', ln=True)
        features = data['features']
        pdf.cell(200, 10, txt=f'Number of Features: {len(features)}', ln=True)
        if features:
            props = ', '.join(features[0]['properties'].keys())
            pdf.multi_cell(200, 10, txt=f'Properties: {props}')
        pdf.output('./tmp.pdf')
        self.s3.upload_file('./tmp.pdf', BUCKET_NAME, path.replace('.geojson', '.pdf'))
        os.remove('./tmp.pdf')
