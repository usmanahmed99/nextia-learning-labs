"""The object-storage contract: what the API needs from a place that keeps files.

The API never sends a file through itself. It gives the client a signed URL: a
link that allows one action (upload or download) on one file, until it expires.
The file's details (name, size, checksum, owner) stay in PostgreSQL.

Two implementations:
- AzureBlobStore: Azure Blob Storage, or Azurite (Microsoft's emulator) on your
  computer. Signed URLs are SAS URLs (shared access signatures).
- LocalFileStore: a folder on disk, for the tests. Its signed URLs are checked by
  `verify()`, with the same rules: one file, one action, an expiry time.

A signed upload URL cannot limit the size of the upload (an Azure SAS has no
size condition). So the API checks the size after the upload, and deletes a
file that is too large.
"""

import hashlib
import hmac
import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, quote, urlencode, urlparse


class FileStore(Protocol):
    def upload_url(
        self, key: str, content_type: str, seconds: int
    ) -> tuple[str, dict[str, str], datetime]: ...
    def download_url(self, key: str, seconds: int, file_name: str) -> tuple[str, datetime]: ...
    def size(self, key: str) -> int | None: ...
    def read(self, key: str) -> bytes: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def delete(self, key: str) -> bool: ...
    def keys(self, prefix: str = "") -> Iterator[str]: ...


def expiry(seconds: int) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0)


class AzureBlobStore:
    """Azure Blob Storage or Azurite, through the azure-storage-blob package."""

    def __init__(
        self, connection_string: str, container: str = "attachments", public_url: str | None = None
    ):
        from azure.storage.blob import BlobServiceClient

        self.service = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container
        self.container = self.service.get_container_client(container)
        # The address that clients use. In Docker Compose the API reaches Azurite as
        # "azurite", but your browser reaches it as 127.0.0.1.
        self.public_url = (public_url or self.service.url).rstrip("/")
        self.account_name = self.service.credential.account_name
        self.account_key = self.service.credential.account_key

    def ensure_container(self) -> None:
        from azure.core.exceptions import ResourceExistsError

        try:
            self.container.create_container()
        except ResourceExistsError:
            pass

    def _sas(self, key: str, permission, until: datetime, **extra) -> str:
        from azure.storage.blob import generate_blob_sas

        return generate_blob_sas(
            self.account_name,
            self.container_name,
            key,
            account_key=self.account_key,
            permission=permission,
            expiry=until,
            **extra,
        )

    def _url(self, key: str, sas: str) -> str:
        return f"{self.public_url}/{self.container_name}/{quote(key)}?{sas}"

    def upload_url(self, key, content_type, seconds):
        from azure.storage.blob import BlobSasPermissions

        until = expiry(seconds)
        sas = self._sas(key, BlobSasPermissions(create=True, write=True), until)
        return (
            self._url(key, sas),
            {"x-ms-blob-type": "BlockBlob", "Content-Type": content_type},
            until,
        )

    def download_url(self, key, seconds, file_name):
        from azure.storage.blob import BlobSasPermissions

        until = expiry(seconds)
        sas = self._sas(
            key,
            BlobSasPermissions(read=True),
            until,
            content_disposition=f'attachment; filename="{file_name}"',
        )
        return self._url(key, sas), until

    def size(self, key):
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self.container.get_blob_client(key).get_blob_properties().size
        except ResourceNotFoundError:
            return None

    def read(self, key):
        return self.container.get_blob_client(key).download_blob().readall()

    def put(self, key, data, content_type):
        from azure.storage.blob import ContentSettings

        self.container.get_blob_client(key).upload_blob(
            data, overwrite=True, content_settings=ContentSettings(content_type=content_type)
        )

    def delete(self, key):
        from azure.core.exceptions import ResourceNotFoundError

        try:
            self.container.get_blob_client(key).delete_blob()
            return True
        except ResourceNotFoundError:
            return False

    def keys(self, prefix=""):
        for blob in self.container.list_blobs(name_starts_with=prefix or None):
            yield blob.name


class LinkRefused(Exception):
    """A signed URL is expired, changed, or for another action."""


class LocalFileStore:
    """Files in a folder; signed URLs that `verify()` checks (for the tests)."""

    def __init__(self, root: Path, secret: bytes = b"local-test-secret"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.secret = secret

    def _sign(self, key: str, action: str, until: int) -> str:
        message = f"{action}\n{key}\n{until}".encode()
        return hmac.new(self.secret, message, hashlib.sha256).hexdigest()

    def _url(self, key: str, action: str, seconds: int) -> tuple[str, datetime]:
        until = expiry(seconds)
        stamp = int(until.timestamp())
        query = urlencode(
            {"action": action, "expires": stamp, "sig": self._sign(key, action, stamp)}
        )
        return f"local://{quote(key)}?{query}", until

    def upload_url(self, key, content_type, seconds):
        url, until = self._url(key, "upload", seconds)
        return url, {"Content-Type": content_type}, until

    def download_url(self, key, seconds, file_name):
        return self._url(key, "download", seconds)

    def verify(self, url: str, action: str, now: float | None = None) -> str:
        """Return the key that a signed URL allows `action` on, or raise LinkRefused."""
        parts = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(parts.query).items()}
        key = parts.netloc + parts.path
        from urllib.parse import unquote

        key = unquote(key)
        if q.get("action") != action:
            raise LinkRefused("this link is for another action")
        if not hmac.compare_digest(
            q.get("sig", ""), self._sign(key, action, int(q.get("expires", 0)))
        ):
            raise LinkRefused("the signature does not match")
        if (now or time.time()) > int(q["expires"]):
            raise LinkRefused("the link has expired")
        return key

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"key outside the store: {key}")
        return path

    def size(self, key):
        p = self._path(key)
        return p.stat().st_size if p.exists() else None

    def read(self, key):
        return self._path(key).read_bytes()

    def put(self, key, data, content_type):
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def delete(self, key):
        p = self._path(key)
        if not p.exists():
            return False
        p.unlink()
        return True

    def keys(self, prefix=""):
        for p in sorted(self.root.rglob("*")):
            if p.is_file():
                key = p.relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    yield key


def make_store(settings) -> FileStore | None:
    if not settings.storage_connection_string:
        return None
    store = AzureBlobStore(
        settings.storage_connection_string, settings.storage_container, settings.storage_public_url
    )
    return store
