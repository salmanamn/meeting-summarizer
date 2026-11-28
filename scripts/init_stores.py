"""Create the local stores (emulators only): blob containers `incoming` and `transcripts` in Azurite, database
`meetings` with container `jobs` (partition key /id) in the Cosmos emulator, and the queue `meeting-events` that
the queue trigger reads (D55; unused by the blob trigger). Safe to run again.

uv run python scripts/init_stores.py

On Azure, Terraform creates all four (M5): the app's identity gets data-plane roles only, which cannot create
databases or containers, and the app never tries.
"""

import sys

from azure.core.exceptions import ResourceNotFoundError
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceExistsError
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

from meeting.events import EVENTS_QUEUE
from meeting.settings import COSMOS_EMULATOR_ENDPOINT, load


def main() -> int:
    settings = load()
    if settings.recordings_service_uri or settings.cosmos_endpoint.rstrip("/") != COSMOS_EMULATOR_ENDPOINT:
        print("FAIL not the emulators' settings: on Azure the stores come from Terraform")
        return 1
    service = BlobServiceClient.from_connection_string(settings.recordings_connection)
    for name in (settings.incoming_container, settings.transcripts_container):
        container = service.get_container_client(name)
        created = not container.exists()
        if created:
            container.create_container()
        print(f"OK   blob container {name} ({'created' if created else 'exists'})")

    queues = QueueServiceClient.from_connection_string(settings.recordings_connection)
    events = queues.get_queue_client(EVENTS_QUEUE)
    try:
        events.get_queue_properties()
        state = "exists"
    except ResourceNotFoundError:
        events.create_queue()
        state = "created"
    print(f"OK   storage queue {EVENTS_QUEUE} ({state})")

    # Create-and-catch-conflict, not list-then-create: the vNext emulator doesn't implement database/collection feeds.
    client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    try:
        db, state = client.create_database(settings.cosmos_database), "created"
    except CosmosResourceExistsError:
        db, state = client.get_database_client(settings.cosmos_database), "exists"
    print(f"OK   cosmos database {settings.cosmos_database} ({state})")
    try:
        db.create_container(settings.jobs_container, partition_key=PartitionKey(path="/id"))
        state = "created"
    except CosmosResourceExistsError:
        state = "exists"
    print(f"OK   cosmos container {settings.jobs_container}, partition key /id ({state})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
