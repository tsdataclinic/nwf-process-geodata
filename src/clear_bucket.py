from src.common import get_s3_session, BUCKET_NAME


def delete_all_objects():
    s3 = get_s3_session().resource("s3")
    bucket = s3.Bucket(BUCKET_NAME)
    print(f"Deleting all objects in {BUCKET_NAME}")
    bucket.objects.all().delete()
    print(f"Successfully deleted all objects in {BUCKET_NAME}")


if __name__ == "__main__":
    delete_all_objects()
