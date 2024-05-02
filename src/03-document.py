
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
