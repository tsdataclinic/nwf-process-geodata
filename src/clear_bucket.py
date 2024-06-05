from src.common import get_s3_session, BUCKET_NAME
import boto3

def delete_all_objects():
    s3 = get_s3_session().resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    print(f"Deleting all objects in {BUCKET_NAME}")
    bucket.objects.all().delete()
    print(f"Successfully deleted all objects in {BUCKET_NAME}")

def delete_key(key_name):
    s3 = get_s3_session().resource("s3")
    # Delete the specified key (file) from the S3 bucket
    s3.Object(BUCKET_NAME, key_name).delete()
    print(f"Successfully deleted {key_name} from {BUCKET_NAME}")

if __name__ == "__main__":
    delete_all_objects()
