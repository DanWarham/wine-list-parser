import os
from minio import Minio
from minio.error import S3Error

# Load MinIO configuration from environment variables
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "wine-lists")
MINIO_SECURE = os.environ.get("MINIO_SECURE", "0") in ("1", "true", "True")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

# Ensure bucket exists
found = minio_client.bucket_exists(MINIO_BUCKET)
if not found:
    minio_client.make_bucket(MINIO_BUCKET)

def upload_to_minio(file, filename):
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    minio_client.put_object(
        MINIO_BUCKET,
        filename,
        data=file.file,
        length=file_size,
        content_type=file.content_type
    )
    return f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}" 