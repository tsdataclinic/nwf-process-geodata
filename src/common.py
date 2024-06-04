import boto3
import json

SECRETS_PATH = "secrets/aws_secrets.json"
BUCKET_NAME = "dataclinic-nwf"
TARGET_CRS = 4326


def get_aws_creds() -> dict[str, str]:
    with open(SECRETS_PATH, "r") as file:
        return json.load(file)


def get_s3_client():
    session = get_s3_session()
    return session.client("s3")


def get_s3_session() -> boto3.Session:
    aws_creds = get_aws_creds()
    return boto3.Session(
        aws_access_key_id=aws_creds["AccessKeyId"],
        aws_secret_access_key=aws_creds["SecretAccessKey"],
        region_name=aws_creds["Region"],
    )
