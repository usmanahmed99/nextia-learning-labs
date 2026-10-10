"""Files that customers attach to tickets: the file goes to object storage through a
signed URL; its details go to PostgreSQL.

1. POST /v1/tenants/{t}/tickets/{id}/attachments   -> a "pending" row and an upload URL
2. the client PUTs the file to the URL  (the API never sees the bytes)
3. POST /v1/tenants/{t}/attachments/{id}/complete  -> the API checks the file -> "stored"
4. GET /v1/tenants/{t}/attachments/{id}/download   -> a download URL that expires

No database connection is held while the API talks to the object storage.

The authentication course (Module 4): every route runs after the access check, every
lookup has the organization in it, and a signed URL is made only AFTER the check. A signed
URL is a key on its own: whoever has it can use it until it expires (5 minutes for a
download), without signing in. New files go under tenants/<organization>/ in the storage.
"""

import hashlib
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from ticket_api import repository
from ticket_api.errors import FilesUnavailable, UploadRejected
from ticket_api.files import FileStore
from ticket_api.models import AttachmentIn, AttachmentInfo, DownloadLink, ErrorResponse, UploadLink
from ticket_api.tenancy import Caller, require
from ticket_api.tickets import DB, TicketId

router = APIRouter(prefix="/v1/tenants/{tenant}", tags=["attachments"])
AttachmentId = Annotated[uuid.UUID, Path()]
Upload = Annotated[Caller, Depends(require("file.upload"))]
Download = Annotated[Caller, Depends(require("file.read"))]
ERRORS = {
    401: {"model": ErrorResponse, "description": "No identity: sign in or send an access token."},
    403: {"model": ErrorResponse, "description": "A member, but the role or scope is too small."},
    404: {"model": ErrorResponse, "description": "No such organization, ticket or attachment."},
    503: {
        "model": ErrorResponse,
        "description": "The database or the file storage is not available.",
    },
}


def get_files(request: Request) -> FileStore:
    store = request.app.state.files
    if store is None:
        raise FilesUnavailable("File storage is off: STORAGE_CONNECTION_STRING is not set.")
    return store


Files = Annotated[FileStore, Depends(get_files)]


@router.post(
    "/tickets/{ticket_id}/attachments",
    status_code=201,
    summary="Start an upload",
    responses={413: {"model": ErrorResponse, "description": "The file is too large."}, **ERRORS},
)
def start_upload(
    ticket_id: TicketId, file: AttachmentIn, caller: Upload, request: Request, db: DB, files: Files
) -> UploadLink:
    settings = request.app.state.settings
    if file.size_bytes > settings.max_upload_bytes:
        raise UploadRejected(
            f"The file is larger than {settings.max_upload_bytes} bytes.", "file_too_large", 413
        )
    attachment_id = str(uuid.uuid4())
    tenant_id = caller.tenant_id
    key = f"tenants/{tenant_id}/tickets/{ticket_id}/{attachment_id}/{file.file_name}"
    with db.connection(caller.tenant_id) as conn:
        if not repository.ticket_exists(conn, ticket_id, tenant_id=tenant_id):
            raise repository.NotFound(f"Ticket {ticket_id} does not exist.")
        repository.create_attachment(
            conn,
            tenant_id,
            attachment_id,
            ticket_id,
            file.file_name,
            file.content_type,
            file.size_bytes,
            key,
        )
    url, headers, until = files.upload_url(key, file.content_type, settings.upload_url_seconds)
    return UploadLink(
        attachment_id=attachment_id,
        upload_url=url,
        headers=headers,
        expires_at=until,
        max_bytes=settings.max_upload_bytes,
    )


@router.post(
    "/attachments/{attachment_id}/complete",
    summary="Check an uploaded file and keep it",
    responses={
        409: {"model": ErrorResponse, "description": "The file is not uploaded yet."},
        413: {"model": ErrorResponse, "description": "The file is too large."},
        422: {"model": ErrorResponse, "description": "The file is not the one announced."},
        **ERRORS,
    },
)
def complete_upload(
    attachment_id: AttachmentId, caller: Upload, request: Request, db: DB, files: Files
) -> AttachmentInfo:
    limit = request.app.state.settings.max_upload_bytes
    with db.connection(caller.tenant_id) as conn:  # 1. a short read
        row = repository.get_attachment(conn, str(attachment_id), tenant_id=caller.tenant_id)
    if row["status"] == "stored":
        return _info(row)
    if row["status"] == "rejected":
        raise UploadRejected(
            "This upload was rejected. Start a new upload.", "upload_rejected", 409
        )
    size = files.size(row["object_key"])  # 2. the object storage, with no connection held
    if size is None:
        raise UploadRejected("The file is not in storage. Upload it first.", "upload_missing", 409)
    problem = None
    if size > limit:
        problem = UploadRejected(f"The file is larger than {limit} bytes.", "file_too_large", 413)
    elif size != row["size_bytes"]:
        problem = UploadRejected(
            f"The file has {size} bytes, not {row['size_bytes']}.", "size_mismatch", 422
        )
    sha = None
    if problem is None:
        sha = hashlib.sha256(files.read(row["object_key"])).hexdigest()
    else:
        files.delete(row["object_key"])
    # 3. a short write, only if the row is still pending
    with db.connection(caller.tenant_id) as conn:
        updated = repository.finish_attachment(
            conn,
            str(attachment_id),
            tenant_id=caller.tenant_id,
            stored=problem is None,
            size_bytes=size,
            sha256=sha,
        )
    if problem is not None:
        raise problem
    return _info(updated)


@router.get(
    "/attachments/{attachment_id}/download", summary="Get a download link", responses=ERRORS
)
def download(
    attachment_id: AttachmentId, caller: Download, request: Request, db: DB, files: Files
) -> DownloadLink:
    # the organization is in the lookup: the check came first
    with db.connection(caller.tenant_id) as conn:
        row = repository.get_attachment(conn, str(attachment_id), tenant_id=caller.tenant_id)
    if row["status"] != "stored":
        raise repository.NotFound(f"Attachment {attachment_id} is not stored.")
    url, until = files.download_url(
        row["object_key"], request.app.state.settings.download_url_seconds, row["file_name"]
    )
    return DownloadLink(url=url, expires_at=until)


def _info(row: dict) -> AttachmentInfo:
    return AttachmentInfo(**{**row, "attachment_id": str(row["attachment_id"])})
