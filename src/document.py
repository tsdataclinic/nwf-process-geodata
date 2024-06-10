import geopandas as gpd
import pandas as pd
import os
from src.common import TARGET_CRS, get_s3_client, BUCKET_NAME
import geopandas as gpd
import matplotlib.pyplot as plt
from io import BytesIO
import io
from urllib.error import HTTPError
from tqdm import tqdm
from rasterio.io import MemoryFile

from fpdf import FPDF


class DataDocumenter:

    def __init__(self) -> None:
        self.s3 = get_s3_client()
        self.metadata = pd.read_csv("./output_metadata.csv")
        self.metadata = self.metadata.fillna("Not found")
        self.wyoming_area = gpd.read_file("wyoming.geojson").to_crs(32045).area

    def _remove_unsupported_characters(self, text):
        return ''.join([char for char in text if char.encode('latin-1', 'ignore')])

    def _read_s3_gdf(self, key: str) -> gpd.GeoDataFrame:
        obj = self.s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return gpd.read_file(io.BytesIO(obj["Body"].read()))
    
    def _read_s3_raster(self, key: str):
        obj = self.s3.get_object(Bucket=BUCKET_NAME, Key=key)

        with MemoryFile(obj['Body'].read()) as memfile:
            with memfile.open() as src:
            # Read the raster data
                raster_data = src.read()
        return raster_data
    
    def _get_processed_keys(self) -> list[str]:
        """
        Retrieves the keys of the processed datasets from the S3 bucket.

        Returns:
        - list[str], the keys of the processed datasets
        """
        contents = self.s3.list_objects(Bucket=BUCKET_NAME, Prefix="data/processed/")["Contents"]
        processed_keys = [content["Key"] for content in contents]
        return [key for key in processed_keys if key.endswith((".geojson", ".img", ".tif"))]

    def document_processed_data(self) -> None:
        keys = self._get_processed_keys()
        for path in tqdm(keys):
            try:
                print(path)
                key_no_ext = os.path.splitext(path)[0].replace("processed", "raw")
                row = self.metadata[self.metadata['s3_raw_path'].str.startswith(key_no_ext)]
                if not row.empty:
                    self._assemble_and_write_pdf(row, path)
            except Exception as e:
                print(f"Error processing {path}: {e}")
    
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
        pdf = self._add_text_box(pdf, "Data as of year", row.as_of_year.astype(int).iloc[0])
        pdf = self._add_text_box(pdf, "Data clinic team notes", row.notes.iloc[0])
        pdf = self._add_text_box(pdf, "Data license/use constraints", row.use_constraints.iloc[0])


        return pdf

    def _add_text_box(self, pdf, title, text):
        title = self._remove_unsupported_characters(str(title))
        text = self._remove_unsupported_characters(str(text))
        pdf.set_font('helvetica', size=12, style = 'B')
        pdf.multi_cell(200, 10, text = title,  new_x="LMARGIN", new_y="NEXT", align = 'L')
        pdf.set_font('helvetica', size=12)
        pdf.multi_cell(200, 10, text = text,  new_x="LMARGIN", new_y="NEXT", align = 'L', markdown=True)

        return pdf

    def _add_data_content(self, pdf, gdf):
        self._add_text_box(pdf, title="Dataset features", text = ', '.join(gdf.columns))
        self._add_text_box(pdf, title="Number of rows", text = str(gdf.shape[0]))
        self._add_text_box(pdf, title="Geometry types", text = str(gdf.geometry.geom_type.value_counts()))
        self._add_text_box(pdf, title="Percent of Wyoming area covered", text = str(round(100 * gdf.to_crs(32045).area.sum() / self.wyoming_area, 1)))

        return pdf

    def _add_map(self, pdf, gdf):
        pdf.set_font('helvetica', size=12, style='B')
        pdf.multi_cell(200, 10, text="Plot of geometry feature", new_x="LMARGIN", new_y="NEXT", align='L')

        plt.ioff()  
        fig, ax = plt.subplots()  # Create a new figure and axis
        gdf.plot(ax=ax)

        img_buf = BytesIO()
        fig.savefig(img_buf, dpi=200)
        plt.close(fig)  # Close the figure explicitly

        pdf.image(img_buf, w=pdf.epw)
        img_buf.close()

        return pdf
    
    def _add_map_raster(self, pdf, raster_data):
        pdf.set_font('helvetica', size=12, style='B')
        pdf.multi_cell(200, 10, text="Plot of raster data", new_x="LMARGIN", new_y="NEXT", align='L')

        plt.ioff()
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(raster_data[0], cmap='viridis')  # Adjust the band index if needed
        plt.colorbar(im, ax=ax, label='Raster Values')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        plt.tight_layout()

        img_buf = BytesIO()
        fig.savefig(img_buf, format='png', dpi=200)
        plt.close(fig)  # Close the figure explicitly

        pdf.image(img_buf, w=pdf.epw)
        img_buf.close()

        return pdf
    
    def _assemble_and_write_pdf(self, row, path):
        pdf = self._create_empty_pdf()
        pdf = self._add_title(pdf, row)
        pdf = self._add_metadata_content(pdf, row)
        if row["format"].iloc[0] in ["shapefile", "geojson", "gdb"]:
            gdf = self._read_s3_gdf(path)
            pdf = self._add_data_content(pdf, gdf)
            pdf = self._add_map(pdf, gdf)
        else:
            raster = self._read_s3_raster(path)
            pdf = self._add_map_raster(pdf, raster_data=raster)

        self._write_to_pdf(pdf, os.path.splitext(path)[0] + ".pdf")

    def _write_to_pdf(self, pdf, path) -> None:
        pdf.output('./tmp.pdf')
        self.s3.upload_file('./tmp.pdf', BUCKET_NAME, path)
        print(f"Wrote documented data to {path}")
        os.remove('./tmp.pdf')
