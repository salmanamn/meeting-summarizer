"""Emulator fixtures: throwaway blob containers in Azurite and a throwaway Cosmos database, removed afterwards."""

import dataclasses
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))  # fakes.py, factories.py

from meeting.settings import load
from meeting.stores import BlobStore, JobStore


@pytest.fixture(scope="session")
def settings():
    tag = uuid.uuid4().hex[:8]
    return dataclasses.replace(
        load({}),
        incoming_container=f"test-incoming-{tag}",
        transcripts_container=f"test-transcripts-{tag}",
        cosmos_database=f"test-meetings-{tag}",
    )


@pytest.fixture(scope="session")
def blobs(settings):
    store = BlobStore.from_settings(settings)
    for name in (settings.incoming_container, settings.transcripts_container):
        store.service.create_container(name)
    yield store
    for name in (settings.incoming_container, settings.transcripts_container):
        store.service.delete_container(name)


@pytest.fixture(scope="session")
def jobs(settings):
    from azure.cosmos import CosmosClient, PartitionKey

    client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    db = client.create_database(settings.cosmos_database)
    db.create_container(settings.jobs_container, partition_key=PartitionKey(path="/id"))
    yield JobStore.from_settings(settings)
    try:
        client.delete_database(settings.cosmos_database)
    except Exception as exc:  # the vNext emulator sometimes answers 500 here (Project 3 D27); don't fail the run
        print(f"WARN cosmos cleanup: {type(exc).__name__}")
