
import asyncio
import logging
import json
from aiokafka import AIOKafkaConsumer

from docparser.core import process_batch_or_file, process_document
from integretion.minio.minio_service import download_document_from_minio, \
    upload_parse_result_to_minio
from integretion.models import ExtractionRequested


# --- MOCKS/IMPORTS ---
# Assuming these are imported from your actual project structure
# from integration.models import KafkaTopics
class KafkaTopics:
    # Placeholder for your Enum
    EXTRACTION_REQUESTED = "extraction_requested_topic"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class KafkaListener:

    def __init__(self, bootstrap_servers: str, group_id: str, minio_client):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.minio_client = minio_client
        self.consumer = None
        self.running = False

    async def start(self):
        """
        Initializes the consumer and starts the infinite listening loop.
        """
        self.consumer = AIOKafkaConsumer(
            KafkaTopics.EXTRACTION_REQUESTED,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            # Disable auto-commit to ensure we only commit AFTER successful processing
            enable_auto_commit=False,
            auto_offset_reset="earliest"
        )

        logger.info(f"Starting Kafka consumer on topic: {KafkaTopics.EXTRACTION_REQUESTED}...")
        await self.consumer.start()
        self.running = True

        try:
            # The 'async for' loop is the most efficient way to consume with aiokafka
            async for msg in self.consumer:
                if not self.running:
                    break

                try:
                    logger.info(f"[{msg.topic}] offset:{msg.offset} --> Message received")

                    # 1) Deserializza evento
                    data = json.loads(msg.value)
                    event = ExtractionRequested(**data)  # adatta al tuo modello

                    # 2) Scarica il documento da MinIO su file locale
                    local_file = await download_document_from_minio(event, self.minio_client)
                    logger.info(f"File fetched from Minio and saved to: {local_file}")

                    # 3) Processa con la tua libreria (bloccante → meglio in thread)
                    from docparser.core import process_batch_or_file

                    parse_result = await asyncio.to_thread(
                        process_document,
                        str(local_file),  # file_path
                        "output",  # output_root (o quello che vuoi)
                        False,  # use_rapidocr
                        False,  # use_openai
                    )

                    # 4) Carica su MinIO gli output (md, chunks, immagini)
                    await upload_parse_result_to_minio(
                        parse_result,
                        event,
                        self.minio_client,
                    )

                    # 5) Commit se tutto OK
                    await self.consumer.commit()

                except Exception as e:
                    logger.error(f"Error processing message at offset {msg.offset}: {e}")


        except asyncio.CancelledError:
            logger.info("Task cancelled. Shutting down consumer loop...")

        finally:
            # Ensure resources are released
            logger.info("Stopping Kafka consumer...")
            await self.consumer.stop()

    async def stop(self):
        """Gracefully stops the consumer."""
        self.running = False
        if self.consumer:
            await self.consumer.stop()