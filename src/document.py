import geopandas as gpd
import pandas as pd
import os
from src.common import TARGET_CRS, get_s3_client, BUCKET_NAME
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
import io
from urllib.error import HTTPError

from fpdf import FPDF


class DataDocumenter:

    def __init__(self) -> None:
        self.s3 = get_s3_client()
        self.metadata = pd.read_csv("./output_metadata.csv")
        self.metadata = self.metadata.fillna("Information not found")

    def _read_s3_gdf(self, key: str) -> gpd.GeoDataFrame:
        obj = self.s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return gpd.read_file(io.BytesIO(obj["Body"].read()))
    
    def document_processed_data(self) -> None:
        resp = self.s3.list_objects_v2(Bucket=BUCKET_NAME)
        for item in resp.get('Contents', []):
            path = item['Key']
            if path.startswith('data/processed') and not path.endswith('.pdf'):
                print(path)
                row = self.metadata[self.metadata['s3_raw_path'].replace('.zip', '.geojson') == path.replace('processed', 'raw')]
                if row.shape[0] == 1:
                    self._assemble_and_write_pdf(row, path)
    
    def _create_empty_pdf(self):
        pdf = FPDF()
        pdf.add_page()

        return pdf
    
    def _add_title(self, pdf, row):
        pdf.set_font('helvetica', size=16, style='B')
        pdf.cell(200, 10, text=f"Dataset: {row['data_title'].values[0]}", new_x="LMARGIN", new_y="NEXT", align='C')

        return pdf

    def _add_metadata_content(self, pdf, row):
        pdf = self._add_text_box(pdf, "Dataset summary", row.data_summary.iloc[0].replace("\n", " "))
        pdf = self._add_text_box(pdf, "Dataset publisher", row.publisher_fullname.iloc[0])
        pdf = self._add_text_box(pdf, "High level source", row.source.iloc[0])
        pdf = self._add_text_box(pdf, "Original format", row.format.iloc[0])
        pdf = self._add_text_box(pdf, "Homeage link",  f"[{row.homepage.iloc[0]}]({row.homepage.iloc[0]})")
        pdf = self._add_text_box(pdf, "Data download link",  f"[{row.data_link.iloc[0]}]({row.data_link.iloc[0]})")
        pdf = self._add_text_box(pdf, "Metadata link",  f"[{row.metadata_link.iloc[0]}]({row.metadata_link.iloc[0]})")
        pdf = self._add_text_box(pdf, "Data license/use constraints", row.use_constraints.iloc[0])

        return pdf

    def _add_text_box(self, pdf, title, text):
        title = str(title)
        text = str(text)
        pdf.set_font('helvetica', size=12, style = 'B')
        pdf.multi_cell(200, 10, text = title,  new_x="LMARGIN", new_y="NEXT", align = 'L')
        pdf.set_font('helvetica', size=12)
        pdf.multi_cell(200, 10, text = text,  new_x="LMARGIN", new_y="NEXT", align = 'L', markdown=True)

        return pdf

    def _add_data_content(self, pdf, gdf):
        self._add_text_box(pdf, title="Dataset features", text = ', '.join(gdf.columns))
        self._add_text_box(pdf, title="Number of rows", text = str(gdf.shape[0]))

        return pdf

    def _add_map(self, pdf, gdf):
        pdf.set_font('helvetica', size=12, style = 'B')
        pdf.multi_cell(200, 10, text = "Plot of geometry feature",  new_x="LMARGIN", new_y="NEXT", align = 'L')

        plt.ioff()  
        plt.figure()
        gdf.plot()

        img_buf = BytesIO()
        plt.savefig(img_buf, dpi=200)
        plt.close()

        pdf.image(img_buf, w=pdf.epw)
        img_buf.close()

        return pdf
    
    def _assemble_and_write_pdf(self, row, path):
        gdf = self._read_s3_gdf(path)

        pdf = self._create_empty_pdf()
        pdf = self._add_title(pdf, row)
        pdf = self._add_metadata_content(pdf, row)
        pdf = self._add_data_content(pdf, gdf)
        pdf = self._add_map(pdf, gdf)

        self._write_to_pdf(pdf, path.replace('.geojson', '.pdf'))

    def _write_to_pdf(self, pdf, path) -> None:
        pdf.output('./tmp.pdf')
        self.s3.upload_file('./tmp.pdf', BUCKET_NAME, path)
        os.remove('./tmp.pdf')
