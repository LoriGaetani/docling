
import asyncio
import logging
import json
from aiokafka import AIOKafkaConsumer


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
                if not self.running: break

                try:
                    logger.info(f"[{msg.topic}] offset:{msg.offset} --> Message received")

                    # 1. Parse the data
                    data_str = msg.value.decode('utf-8')
                    # payload = json.loads(data_str) # Uncomment if payload is JSON

                    # 2. Business Logic (e.g., Minio operations)
                    # await self.process_data(data_str)

                    # 3. Manual Commit
                    # Crucial: Since enable_auto_commit=False, we must commit manually.
                    # We do this only if the logic above succeeded.
                    await self.consumer.commit()

                except Exception as e:
                    # Catch processing errors so the consumer doesn't crash on one bad message
                    logger.error(f"Error processing message at offset {msg.offset}: {e}")
                    # Strategy decision: Do you want to skip it? Or stop?
                    # Currently, it logs the error and continues to the next message.

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