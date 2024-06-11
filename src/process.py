# %%
import io
import os
import geopandas as gpd
from common import TARGET_CRS, get_s3_client, BUCKET_NAME
from tqdm import tqdm
import tempfile
from rasterio.mask import mask
import zipfile
from rasterio.warp import calculate_default_transform, reproject, Resampling
from process_LOCA import main_process_LOCA
# Permitted suffixes for reading geopandas datasets.
PERMITTED_SUFFIXES = (".geojson", ".zip", ".tif", ".img", ".tar.gz")

SPECIAL_CASE_KEYS = ["data/raw/climate_change_indicators/flooding/loca_precipitation/loca_precipitation.tar.gz",
                     "data/raw/climate_change_indicators/extreme_heat/loca_extreme_temperature_forecast/loca_extreme_temperature_forecast.tar.gz",
                     "data/raw/climate_change_indicators/drought/loca_dry_days_forecast/loca_dry_days_forecast.tar.gz"]

GDBs = {"data/raw/crucial_critical/blm/areas_of_critical_environmental_concern/areas_of_critical_environmental_concern.zip" : "a00000028.gdbtable", 
        "data/raw/climate_change_indicators/flooding/fema_nfhl/fema_nfhl.zip" : "a00000015.gdbtable"}

class Processor:

    def __init__(self, bucket_name=BUCKET_NAME, noupload=False):
        self.s3 = get_s3_client()
        self.wyoming_gdf = self._get_wyoming_gdf()
        self.bucket_name = bucket_name
        self.noupload = noupload
        self.raw_keys = self._get_raw_keys(bucket_name=bucket_name)
        self.processed_keys = self._get_processed_keys(bucket_name=bucket_name)

    def _get_wyoming_gdf(self) -> gpd.GeoDataFrame:
        return gpd.read_file("wyoming.geojson")

    def _get_raw_keys(self, bucket_name=None) -> list[str]:
        all_keys = self._get_all_keys(bucket_name=bucket_name)
        return [key for key in all_keys if key.startswith("data/raw")]

    def _get_processed_keys(self, bucket_name=None) -> set[str]:
        all_keys = self._get_all_keys(bucket_name=bucket_name)
        return {key for key in all_keys if key.startswith("data/processed")}

    def _get_all_keys(self, bucket_name=None) -> list[str]:
        """
        Retrieves the keys of the raw datasets from the S3 bucket.

        Returns:
        - list[str], the keys of the raw datasets
        """
        contents = self.s3.list_objects(Bucket=bucket_name)["Contents"]
        raw_keys = [content["Key"] for content in contents]
        return [key for key in raw_keys if key.endswith(PERMITTED_SUFFIXES)]

    def process_raw_datasets(self, overwrite=False):
        """
        Walks through 'data/raw' directory on 'dataclinic-nwf' bucket and performs processing steps
        to output files while preserving the directory structure from the raw directory.

        Parameters:
        - overwrite: bool, if False, files that are already on the bucket are not replaced.
        """

        for raw_key in tqdm(self.raw_keys):
            print(f"Processing {raw_key}")

            if not overwrite and self.is_processed(raw_key):
                print(f"Skipping {raw_key}, which has already been processed.")
                continue

            try:
                self._process_raw_dataset(raw_key)
            except Exception as e:
                print(f"Error processing {raw_key}: {e}")

    def _process_raw_dataset(self, raw_key):
        if raw_key.endswith((".img", ".tif")):
           print(f"Copying raster {raw_key}")
           self.s3.copy_object(
            Bucket=self.bucket_name,
            Key=raw_key.replace("raw", "processed", 1),
            CopySource={'Bucket': self.bucket_name, 'Key': raw_key})
        elif raw_key in SPECIAL_CASE_KEYS:
            print(f"Processing {raw_key}")
            processed_key = self._to_processed_key(raw_key, fmt = "tif").replace(".tar", "")
            directory = os.path.dirname(processed_key)
            os.makedirs(directory, exist_ok=True)
            main_process_LOCA(self.s3, self.bucket_name, raw_key, processed_key, processed_key)
            self.s3.upload_file(processed_key, self.bucket_name, processed_key)
        else:
           self._process_raw_vector_dataset(raw_key)
    
    def _process_raw_vector_dataset(self, raw_key: str):
        gdf = self._read_s3_gdf(raw_key)
        gdf = self._reproject(gdf, TARGET_CRS)
        gdf = self._intersect_with_wyoming_boundaries(gdf)

        if gdf.empty:
            print(f"Warning: {raw_key} is empty after processing.")
            return
        self._write_processed(gdf, self._to_processed_key(raw_key))

    def is_processed(self, raw_key: str, fmt = "geojson") -> bool:
        return self._to_processed_key(raw_key) in self.processed_keys
    
    def _read_layer_from_zipped_gdb(self, raw_key, layer_name):
        response = self.s3.get_object(Bucket=self.bucket_name, Key=raw_key)
        gdb_zip = io.BytesIO(response['Body'].read())
        with tempfile.TemporaryDirectory() as tmpdirname:
            with zipfile.ZipFile(gdb_zip, 'r') as z:
                z.extractall(tmpdirname)
                
            gdb_folder = [f for f in os.listdir(tmpdirname) if f.endswith('.gdb')][0]
            gdb_path = os.path.join(tmpdirname, gdb_folder) + "/" + layer_name
            gdf = gpd.read_file(gdb_path)
            
            gdf = gdf[gdf.geometry.notnull()]
            gdf['geometry'] = gdf.geometry.apply(lambda x: x if x.is_valid else x.buffer(0))
            gdf['geometry'] = gdf.geometry.simplify(tolerance=0.0001)

        return gdf
    
    def _read_s3_gdf(self, key: str) -> gpd.GeoDataFrame:

        if key in GDBs.keys():
            gdf = self._read_layer_from_zipped_gdb(key, GDBs[key])
            return gdf
        else:
            obj = self.s3.get_object(Bucket=self.bucket_name, Key=key)
            return gpd.read_file(io.BytesIO(obj["Body"].read()))

    def _to_processed_key(self, raw_key: str, fmt = "geojson") -> str:
        # 1 => Only replace the first occurrence of 'raw' in the path with 'processed'
        processed_key = raw_key.replace("raw", "processed", 1)
        processed_key = ".".join(processed_key.split(".")[:-1] + [fmt])

        return processed_key
    
    def _intersect_with_wyoming_boundaries(self, gdf: gpd.GeoDataFrame):
        """
        Intersects the GeoDataFrame with Wyoming boundaries to trim excess areas.

        Parameters:
        - gdf: GeoDataFrame, the dataset to be trimmed

        Returns:
        - GeoDataFrame, the trimmed dataframe
        """
        return gpd.overlay(gdf, self.wyoming_gdf, how="intersection")

    def _reproject(self, gdf: gpd.GeoDataFrame, output_crs: int):
        """
        Reprojects a GeoDataFrame to a specified coordinate reference system.

        Parameters:
        - gdf: GeoDataFrame, the dataset to reproject
        - output_crs: int, EPSG code for the target CRS

        Returns:
        - GeoDataFrame, the reprojected dataframe
        """
        return gdf.to_crs(epsg=output_crs)

    def _write_processed(self, gdf, processed_key, fmt="geojson"):
        """
        Writes the processed GeoDataFrame to the correct location on the S3 bucket.

        Parameters:
        - gdf: GeoDataFrame, the processed dataset
        - processed_key: str, path to save to
        - format: str, file format for output, default is 'geojson'
        """
        self._write_s3_gdf(gdf, processed_key, fmt)

    def _write_s3_gdf(self, gdf: gpd.GeoDataFrame, key: str, fmt="geojson"):
        try:
            os.makedirs(os.path.dirname(key), exist_ok=True)
            # Make a local copy.
            gdf.to_file(key, format=fmt)
            # Upload to S3.
            if self.noupload:
                self.s3.upload_file(key, self.bucket_name, key)
                print(f"Uploaded {key} to {self.bucket_name}")
        finally:
            pass
            # Clean up the local copy.
            #os.remove(key)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Process raw data")
    parser.add_argument('--s3bucket', type=str, default=BUCKET_NAME,
                        help="The s3 bucket to use for the pipeline")
    parser.add_argument('--noupload', action="store_true", default=False,
                        help="Skip Uploading processed data to s3")
    inputs = parser.parse_args()

    proc = Processor(bucket_name=inputs.s3bucket, noupload=inputs.noupload)
    proc.process_raw_datasets()

