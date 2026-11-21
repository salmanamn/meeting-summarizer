#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["azure-storage-blob==12.31.1", "azure-cosmos==4.17.1"]
# ///
"""SDK smoke test: Azurite blob container create/upload/download/delete + Cosmos vNext emulator CRUD.

Emulator well-known credentials only. Never used against Azure.
"""

import os
import sys
import uuid

from azure.cosmos import CosmosClient, PartitionKey
from azure.storage.blob import BlobServiceClient

BLOB_CONN = os.getenv("BLOB_CONN", "UseDevelopmentStorage=true")
COSMOS_URL = os.getenv("COSMOS_URL", "http://localhost:8081")
COSMOS_KEY = os.getenv(
    "COSMOS_KEY",
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
)


def blob() -> None:
    service = BlobServiceClient.from_connection_string(BLOB_CONN)
    name = f"smoke-{uuid.uuid4().hex[:12]}"
    container = service.create_container(name)
    try:
        data = os.urandom(256 * 1024)  # a quarter of a megabyte, like a short audio chunk
        container.upload_blob("recording.bin", data, metadata={"meeting": "smoke"})
        blob_client = container.get_blob_client("recording.bin")
        if blob_client.download_blob().readall() != data:
            raise RuntimeError("downloaded bytes differ from the upload")
        if blob_client.get_blob_properties().metadata != {"meeting": "smoke"}:
            raise RuntimeError("metadata did not round-trip")
        print("OK   azurite blob create/upload/download/metadata")
    finally:
        container.delete_container()


def cosmos() -> None:
    client = CosmosClient(COSMOS_URL, credential=COSMOS_KEY)
    db = client.create_database_if_not_exists("smoke")
    try:
        container = db.create_container_if_not_exists("items", partition_key=PartitionKey(path="/pk"))
        item = {"id": str(uuid.uuid4()), "pk": "smoke", "value": 42}
        container.upsert_item(item)
        got = container.read_item(item["id"], partition_key="smoke")
        if got["value"] != 42:
            raise RuntimeError(f"unexpected item: {got}")
        print("OK   cosmos create/upsert/read")
    finally:
        client.delete_database("smoke")


def main() -> int:
    failed = False
    for name, check in (("blob", blob), ("cosmos", cosmos)):
        try:
            check()
        except Exception as exc:  # report every check, then fail
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
