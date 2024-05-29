from src.download import DataDownloaderUploader
from src.process import Processor
from src.document import DataDocumenter
from src.export import s3Exporter

DataDownloaderUploader().download_and_upload_main()
Processor().process_raw_datasets()
DataDocumenter().document_processed_data()
s3Exporter().export_all("export_test")