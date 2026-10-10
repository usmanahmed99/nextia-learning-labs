"""Module 5, lesson 1: files go to object storage through signed URLs; their details stay in
PostgreSQL.

Most tests use LocalFileStore (a folder). test_azurite_* run only with `pytest -m azurite`,
against Azurite (docker compose up -d azurite) and STORAGE_CONNECTION_STRING."""

import hashlib
import os
import time
import urllib.error
import urllib.request

import pytest

from ticket_api.files import LinkRefused, LocalFileStore


@pytest.fixture
def api(grace):
    """Since the authentication course, the ticket routes need a member: Grace, at Larkfield."""
    return grace


PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 2000


@pytest.fixture
def store(tmp_path):
    return LocalFileStore(tmp_path / "files")


@pytest.fixture
def files_api(make_api, store):
    api = make_api(user="usr-grace", max_upload_bytes=5000)
    api.app.state.files = store
    return api


def upload(api, store, data=PNG, declared=None, name="photo-1.png"):
    link = api.post(
        "/v1/tenants/larkfield/tickets/T-30002/attachments",
        json={"file_name": name, "content_type": "image/png", "size_bytes": declared or len(data)},
    ).json()
    key = store.verify(link["upload_url"], "upload")
    store.put(key, data, "image/png")
    return link, key


def test_a_signed_url_allows_one_action_on_one_file_until_it_expires(store):
    url, _, until = store.upload_url("tickets/T-1/a/photo.png", "image/png", 60)
    assert store.verify(url, "upload") == "tickets/T-1/a/photo.png"
    with pytest.raises(LinkRefused, match="another action"):
        store.verify(url, "download")
    with pytest.raises(LinkRefused, match="expired"):
        store.verify(url, "upload", now=until.timestamp() + 1)
    with pytest.raises(LinkRefused, match="signature"):
        store.verify(url.replace("T-1", "T-2"), "upload")


def test_upload_complete_download(files_api, store, conn):
    link, key = upload(files_api, store)
    assert (
        conn.execute(
            "SELECT status FROM attachments WHERE attachment_id = %s", (link["attachment_id"],)
        ).fetchone()["status"]
        == "pending"
    )
    done = files_api.post(f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/complete")
    assert done.status_code == 200 and done.json()["status"] == "stored"
    row = conn.execute(
        "SELECT sha256, size_bytes FROM attachments WHERE attachment_id = %s",
        (link["attachment_id"],),
    ).fetchone()
    assert row["sha256"] == hashlib.sha256(PNG).hexdigest() and row["size_bytes"] == len(PNG)
    url = files_api.get(
        f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/download"
    ).json()["url"]
    assert store.read(store.verify(url, "download")) == PNG
    names = [
        a["file_name"]
        for a in files_api.get("/v1/tenants/larkfield/tickets/T-30002").json()["attachments"]
    ]
    assert "photo-1.png" in names


def test_completing_twice_is_harmless(files_api, store):
    link, _ = upload(files_api, store)
    first = files_api.post(
        f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/complete"
    ).json()
    second = files_api.post(
        f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/complete"
    ).json()
    assert first == second


def test_a_file_that_is_too_large_is_refused_before_the_upload(files_api):
    response = files_api.post(
        "/v1/tenants/larkfield/tickets/T-30002/attachments",
        json={"file_name": "big.png", "content_type": "image/png", "size_bytes": 6000},
    )
    assert response.status_code == 413


def test_a_larger_file_than_announced_is_deleted(files_api, store, conn):
    """A signed URL cannot limit the size: the API checks it after the upload."""
    link, key = upload(files_api, store, data=b"x" * 7000, declared=100)
    response = files_api.post(f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/complete")
    assert response.status_code == 413
    assert store.size(key) is None
    assert (
        conn.execute(
            "SELECT status FROM attachments WHERE attachment_id = %s", (link["attachment_id"],)
        ).fetchone()["status"]
        == "rejected"
    )


def test_complete_before_upload_is_409(files_api):
    link = files_api.post(
        "/v1/tenants/larkfield/tickets/T-30002/attachments",
        json={"file_name": "a.png", "content_type": "image/png", "size_bytes": 10},
    ).json()
    assert (
        files_api.post(
            f"/v1/tenants/larkfield/attachments/{link['attachment_id']}/complete"
        ).status_code
        == 409
    )


def test_without_object_storage_the_file_endpoints_answer_503(api):
    response = api.post(
        "/v1/tenants/larkfield/tickets/T-30002/attachments",
        json={"file_name": "a.png", "content_type": "image/png", "size_bytes": 10},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "files_unavailable"


def test_a_file_name_cannot_climb_out_of_its_folder(files_api):
    response = files_api.post(
        "/v1/tenants/larkfield/tickets/T-30002/attachments",
        json={"file_name": "../../x.png", "content_type": "image/png", "size_bytes": 10},
    )
    assert response.status_code == 422


# ---------- the real thing: Azurite and SAS URLs (pytest -m azurite) ----------

AZURITE = os.environ.get("STORAGE_CONNECTION_STRING")


def http(method, url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.mark.azurite
@pytest.mark.skipif(not AZURITE, reason="STORAGE_CONNECTION_STRING is not set")
def test_azurite_sas_upload_download_expiry_and_scope():
    from ticket_api.files import AzureBlobStore

    store = AzureBlobStore(AZURITE, "test-attachments")
    store.ensure_container()
    key = "tickets/T-1/test/photo.png"
    url, headers, _ = store.upload_url(key, "image/png", 60)
    assert http("PUT", url, PNG, headers)[0] == 201
    assert http("PUT", url, b"y" * 20000, headers)[0] == 201  # no size limit in a SAS
    assert store.size(key) == 20000
    down, _ = store.download_url(key, 2, "photo.png")
    assert http("GET", down)[0] == 200
    assert http("GET", url)[0] == 403  # an upload URL cannot download
    other = down.replace("photo.png?", "other.png?")
    assert http("GET", other)[0] == 403  # a URL for one file only
    time.sleep(3)
    assert http("GET", down)[0] == 403  # expired
    assert store.delete(key) and store.size(key) is None
