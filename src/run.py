from download import DataDownloaderUploader
from process import Processor
from document import DataDocumenter
from export import s3Exporter
from common import BUCKET_NAME
import argparse

def parse_args():
    """Parse args"""
    parser = argparse.ArgumentParser(description="Run pipeline for parsing data")
    parser.add_argument('--s3bucket', type=str, default=BUCKET_NAME,
                        help="The s3 bucket to use for the pipeline")
    parser.add_argument('--noupload', action="store_true", default=False,
                        help="Skip Uploading processed data to s3")
    parser.add_argument('--overwrite', action="store_true", default=False,
                        help="Overwrite data already processed")
    parser.add_argument('--export-local', action="store_true", default=False,
                        help="Export everything to the export_local directory")
    parser.add_argument('--local-download-dir', type=str, default='export_local',
                        help="The local directory to export all data")
    return parser.parse_args()

if __name__ == "__main__":
    inputs = parse_args()

    print('*** Downloading raw data and uploading to s3 ***')
    ddu = DataDownloaderUploader(bucket_name=inputs.s3bucket,
                                 noupload=inputs.noupload,
                                 overwrite=inputs.overwrite)
    ddu.download_and_upload_main()

    print('*** Processing raw data ***')
    proc = Processor(bucket_name=inputs.s3bucket, noupload=inputs.noupload)
    proc.process_raw_datasets()

    print('*** Generating pdf documents ***')
    dd = DataDocumenter(bucket_name=inputs.s3bucket, noupload=inputs.noupload)
    dd.document_processed_data()

    if inputs.export_local:
        print('*** Exporting data locally ***')
        s3e = s3Exporter(bucket_name=inputs.s3bucket,
                         local_download_dir=inputs.local_download_dir)
        s3e.export_all()

