import os
from pathlib import Path

from minio import Minio

from docparser.pipeline import DoclingParseResult
from integretion.models import ExtractionRequested


def get_client():
    return Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )



async def upload_parse_result_to_minio(
    result: DoclingParseResult,
    event: ExtractionRequested,
    minio_client: Minio,
) -> None:
    """
    Carica su MinIO:
    - markdown
    - chunks
    - immagini (se ci sono)
    usando collectionId/documentId per costruire i path.
    """
    bucket = f"bucket-{event.collection_id}"
    if not minio_client.bucket_exists(bucket):
        minio_client.make_bucket(bucket)

    # 1) Markdown
    minio_client.fput_object(
        bucket_name=bucket,
        object_name=f"{event.object_key}/output.md",
        file_path=str(result.markdown_path),
        part_size=10 * 1024 * 1024,
        content_type="text/markdown",
    )

    # 2) Chunks
    minio_client.fput_object(
        bucket_name=bucket,
        object_name=f"{event.object_key}/chunks.json",
        file_path=str(result.chunks_path),
        part_size=10 * 1024 * 1024,
        content_type="application/json",
    )

    # 3) Immagini
    if result.images_dir and result.images_dir.exists():
        for img_path in result.images_dir.glob("*"):
            object_name = f"{event.object_key}/images/{img_path.name}"
            minio_client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=str(img_path),
                part_size=10 * 1024 * 1024,
            )


#TODO ritorno inputstream o file intero?
async def download_document_from_minio(
    event: ExtractionRequested,
    minio_client: Minio,
) -> Path:
    """
    Scarica il documento da MinIO su file system locale
    e ritorna il Path al file.
    """

    base_dir = Path("/tmp/docparser") / str(event.collection_id)
    base_dir.mkdir(parents=True, exist_ok=True)

    local_path = base_dir / event.file_name

    minio_client.fget_object(
        bucket_name=event.bucket,
        object_name=event.object_key,
        file_path=str(local_path),
    )

    return local_path