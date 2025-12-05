import asyncio

from integretion.events.kafka_listener import KafkaListener
from integretion.minio.minio_service import get_client


async def main():
    """
    Main orchestrator function.
    """
    # 1. Setup dependencies (Mocking Minio for this example)
    minio = get_client()

    # 2. Instantiate the Listener
    listener = KafkaListener(
        bootstrap_servers="localhost:9092",
        group_id="my-group-v1",
        minio_client=minio
    )

    # 3. Start the listener
    # This will block execution here as long as the listener is running
    await listener.start()


if __name__ == "__main__":
    print("🚀 Application starting...")

    try:
        # asyncio.run() handles the creation and closing of the event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Application stopped manually (CTRL+C)")
