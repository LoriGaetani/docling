import os
from pathlib import Path

from minio import Minio

from integretion.models import ExtractionRequested


def get_client():
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )




async def upload_from_fastapi(file_path: str, collectionId: str, documentId: str, objectKey: str, minio_client: Minio):
    if not os.path.exists(file_path):
        print(f"Errore: file '{file_path}' does not exist.")
        return

    bucket = f"bucket-{collectionId}"
    object_name = f"/{documentId}/images/{objectKey}"

    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)

    minio_client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=file_path,
        part_size=10 * 1024 * 1024,  # 10MB
        content_type=file.content_type,
    )

    return {"status": "ok"}


#TODO ritorno inputstream o file intero?
def process_document_from_minio(event: ExtractionRequested, minio_client: Minio):

    doc = minio_client.get_object(event.bucket, event.object_key)

    try:
        result = doc.read()
        print(result)
        return result

    finally:
        doc.close()
        doc.release_conn()