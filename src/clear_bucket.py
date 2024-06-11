from common import get_s3_session, BUCKET_NAME
import boto3
import argparse

def delete_all_objects(bucket_name=BUCKET_NAME):
    s3 = get_s3_session().resource("s3")
    bucket = s3.Bucket(bucket_name)
    print(f"Deleting all objects in {bucket_name}")
    bucket.objects.all().delete()
    print(f"Successfully deleted all objects in {bucket_name}")

def delete_key(key_name=None, bucket_name=BUCKET_NAME):
    s3 = get_s3_session().resource("s3")
    # Delete the specified key (file) from the S3 bucket
    s3.Object(bucket_name, key_name).delete()
    print(f"Successfully deleted {key_name} from {bucket_name}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Delete all objects")
    parser.add_argument('--s3bucket', type=str, default=BUCKET_NAME,
                        help="The s3 bucket to use for the pipeline")
    inputs = parser.parse_args()

    delete_all_objects(bucket_name=inputs.s3bucket)
