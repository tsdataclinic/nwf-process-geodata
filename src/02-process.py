# %%
import io
import os
import geopandas as gpd
from common import TARGET_CRS, get_s3_client, BUCKET_NAME
from tqdm import tqdm
import boto3

# Permitted suffixes for reading geopandas datasets.
PERMITTED_SUFFIXES = (".geojson", ".zip")


class Processor:

    def __init__(self):
        self.s3 = get_s3_client()
        self.wyoming_gdf = self._get_wyoming_gdf()
        self.raw_keys = self._get_raw_keys()
        self.processed_keys = self._get_processed_keys()

    def _get_wyoming_gdf(self) -> gpd.GeoDataFrame:
        return gpd.read_file("wyoming.geojson")

    def _get_raw_keys(self) -> list[str]:
        all_keys = self._get_all_keys()
        return [key for key in all_keys if key.startswith("data/raw")]

    def _get_processed_keys(self) -> set[str]:
        all_keys = self._get_all_keys()
        return {key for key in all_keys if key.startswith("data/processed")}

    def _get_all_keys(self) -> list[str]:
        """
        Retrieves the keys of the raw datasets from the S3 bucket.

        Returns:
        - list[str], the keys of the raw datasets
        """
        contents = self.s3.list_objects(Bucket=BUCKET_NAME)["Contents"]
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

    def _process_raw_dataset(self, raw_key: str):
        gdf = self._read_s3_gdf(raw_key)
        gdf = self._reproject(gdf, TARGET_CRS)
        gdf = self._intersect_with_wyoming_boundaries(gdf)

        if gdf.empty:
            print(f"Warning: {raw_key} is empty after processing.")
            return
        self._write_processed(gdf, self._to_processed_key(raw_key))

    def is_processed(self, raw_key: str) -> bool:
        return self._to_processed_key(raw_key) in self.processed_keys

    def _read_s3_gdf(self, key: str) -> gpd.GeoDataFrame:
        obj = self.s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return gpd.read_file(io.BytesIO(obj["Body"].read()))

    def _to_processed_key(self, raw_key: str) -> str:
        # 1 => Only replace the first occurrence of 'raw' in the path with 'processed'
        return raw_key.replace("raw", "processed", 1)

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
        processed_key = ".".join(processed_key.split(".")[:-1] + [fmt])
        self._write_s3_gdf(gdf, processed_key, fmt)

    def _write_s3_gdf(self, gdf: gpd.GeoDataFrame, key: str, fmt="geojson"):
        try:
            os.makedirs(os.path.dirname(key), exist_ok=True)
            # Make a local copy.
            gdf.to_file(key, format=fmt)
            # Upload to S3.
            self.s3.upload_file(key, BUCKET_NAME, key)
        finally:
            # Clean up the local copy.
            os.remove(key)


if __name__ == "__main__":
    Processor().process_raw_datasets(overwrite=False)
