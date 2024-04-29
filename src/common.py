import boto3
import json

SECRETS_PATH = "secrets/aws_secrets.json"
BUCKET_NAME = "dataclinic-nwf"
TARGET_CRS = 4362


def get_aws_creds() -> dict[str, str]:
    with open(SECRETS_PATH, "r") as file:
        return json.load(file)


def get_s3_client():
    aws_creds = get_aws_creds()
    session = boto3.Session(
        aws_access_key_id=aws_creds["AccessKeyId"],
        aws_secret_access_key=aws_creds["SecretAccessKey"],
        region_name=aws_creds["Region"],
    )
    return session.client("s3")
