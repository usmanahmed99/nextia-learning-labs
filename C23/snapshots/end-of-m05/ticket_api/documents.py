"""Search an organization's help documents, with citations (the authentication course, Module 4).

GET /v1/tenants/{tenant}/documents?q=refund

Two permissions shape the answer: the organization (only its own documents) and the role
(staff-only documents only for owner and staff). Both are in the query and in the cache key,
so an answer made for one caller is never served to a caller who may see less.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from ticket_api import repository
from ticket_api.cache import cache_key
from ticket_api.deps import DB
from ticket_api.models import DocumentResults, ErrorResponse
from ticket_api.tenancy import Caller, require

router = APIRouter(prefix="/v1/tenants/{tenant}", tags=["documents"])


@router.get(
    "/documents",
    summary="Search the help documents",
    responses={
        401: {"model": ErrorResponse, "description": "No identity."},
        404: {"model": ErrorResponse, "description": "No such organization or membership."},
    },
)
def search(
    caller: Annotated[Caller, Depends(require("document.read"))],
    db: DB,
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=200)],
) -> DocumentResults:
    staff = caller.may("document.read_staff")
    level = "staff" if staff else "public"
    key = cache_key(caller.tenant_id, "documents", level, q.lower())
    cached = request.app.state.cache.get(key)
    if cached is not None:
        return cached
    with db.connection(caller.tenant_id) as conn:
        rows = repository.search_documents(conn, q, tenant_id=caller.tenant_id, staff=staff)
    result = DocumentResults(access_level=level, results=rows)
    request.app.state.cache.set(key, result)
    return result
