"""Blob storage and Cosmos DB for the job (D17). Keys and connection strings only for the emulators; on Azure the
same classes get the app's managed identity, chosen by which settings are present (D8).

The job (`meeting.job`) only talks to the two small classes here, so its tests use in-memory fakes with the same
methods (tests/unit/fakes.py) and these classes are tested against Azurite and the Cosmos emulator
(tests/integration).
"""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from azure.core import MatchConditions
from azure.core.exceptions import ResourceNotFoundError

from meeting.settings import Settings

CHUNK = 4 * 1024 * 1024


class TooLarge(ValueError):
    """A blob is larger than the limit given; reading stopped at the limit."""


class Conflict(RuntimeError):
    """A job record changed since it was read (another delivery wrote first), or already exists."""


@dataclass(frozen=True)
class BlobInfo:
    size: int
    etag: str


def _credential():
    from azure.identity import DefaultAzureCredential  # managed identity on Azure (AZURE_CLIENT_ID picks it)

    return DefaultAzureCredential()


class BlobStore:
    def __init__(self, service, incoming: str, transcripts: str) -> None:
        self.service = service  # public: the upload script writes through the same client
        self.incoming = incoming
        self.transcripts = transcripts

    @classmethod
    def from_settings(cls, settings: Settings) -> "BlobStore":
        from azure.storage.blob import BlobServiceClient

        if settings.recordings_service_uri:
            service = BlobServiceClient(settings.recordings_service_uri, credential=_credential())
        else:
            service = BlobServiceClient.from_connection_string(settings.recordings_connection)
        return cls(service, settings.incoming_container, settings.transcripts_container)

    def _blob(self, container: str, name: str):
        return self.service.get_blob_client(container, name)

    def read(self, container: str, name: str, max_bytes: int) -> tuple[bytes, str] | None:
        """Content and ETag from one request (so they belong together), or None when the blob doesn't exist."""
        try:
            downloader = self._blob(container, name).download_blob(offset=0, length=max_bytes + 1)
        except ResourceNotFoundError:
            return None
        if downloader.properties.size > max_bytes:
            raise TooLarge(f"{name} is larger than {max_bytes} bytes")
        return downloader.readall(), downloader.properties.etag

    def info(self, container: str, name: str) -> BlobInfo | None:
        try:
            props = self._blob(container, name).get_blob_properties()
        except ResourceNotFoundError:
            return None
        return BlobInfo(size=props.size, etag=props.etag)

    def url(self, container: str, name: str) -> str:
        """The blob's plain URL (no SAS): what Speech batch transcription reads with its own identity (D3)."""
        return self._blob(container, name).url

    def head(self, container: str, name: str, length: int) -> bytes:
        return self._blob(container, name).download_blob(offset=0, length=length).readall()

    def sha256(self, container: str, name: str, max_bytes: int, target: Path | None = None) -> str:
        """Stream the blob, hashing it (and writing it to `target` when given); stops at max_bytes."""
        digest, seen = hashlib.sha256(), 0
        out = target.open("wb") if target else None
        try:
            for chunk in self._blob(container, name).download_blob(max_concurrency=2).chunks():
                seen += len(chunk)
                if seen > max_bytes:
                    raise TooLarge(f"{name} is larger than {max_bytes} bytes")
                digest.update(chunk)
                if out:
                    out.write(chunk)
        finally:
            if out:
                out.close()
        return digest.hexdigest()

    def write_text(self, container: str, name: str, text: str) -> None:
        self._blob(container, name).upload_blob(text.encode("utf-8"), overwrite=True)

    def read_text(self, container: str, name: str) -> str | None:
        try:
            return self._blob(container, name).download_blob().readall().decode("utf-8")
        except ResourceNotFoundError:
            return None


class JobStore:
    """Job records in Cosmos DB, one per meeting, partition key /id. Every change after the first write is a
    replace conditioned on the record's ETag, so two deliveries of the same event cannot both win (D18)."""

    def __init__(self, container) -> None:
        self._container = container

    @classmethod
    def from_settings(cls, settings: Settings) -> "JobStore":
        from azure.cosmos import CosmosClient

        credential = settings.cosmos_key or _credential()
        client = CosmosClient(
            settings.cosmos_endpoint,
            credential=credential,
            enable_endpoint_discovery=settings.cosmos_endpoint_discovery,
        )
        return cls(client.get_database_client(settings.cosmos_database).get_container_client(settings.jobs_container))

    def get(self, job_id: str) -> dict | None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        try:
            return dict(self._container.read_item(job_id, partition_key=job_id))
        except CosmosResourceNotFoundError:
            return None

    def create(self, doc: dict) -> dict:
        from azure.cosmos.exceptions import CosmosResourceExistsError

        try:
            return dict(self._container.create_item(doc))
        except CosmosResourceExistsError:
            raise Conflict(f"job {doc['id']} already exists") from None

    def replace(self, doc: dict) -> dict:
        from azure.cosmos.exceptions import CosmosAccessConditionFailedError

        body = {k: v for k, v in doc.items() if not k.startswith("_")}
        try:
            return dict(
                self._container.replace_item(
                    doc["id"], body, etag=doc["_etag"], match_condition=MatchConditions.IfNotModified
                )
            )
        except CosmosAccessConditionFailedError:
            raise Conflict(f"job {doc['id']} changed since it was read") from None

    def increment(self, job_id: str, field: str) -> None:
        """A counter that needs no ETag (deliveries, ignored uploads): Cosmos patch `incr` is atomic."""
        self._container.patch_item(
            job_id, partition_key=job_id, patch_operations=[{"op": "incr", "path": f"/{field}", "value": 1}]
        )
