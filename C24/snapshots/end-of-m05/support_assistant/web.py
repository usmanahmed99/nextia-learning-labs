"""A simulated network. The `fetch_url` tool never reaches the internet: it reads from data/web/.

Every host and page is made up. Some hosts are on the shop's allow-list (the supplier, the shop's
own site); others are an attacker's server, a host nobody allowed, the cloud metadata address, or
the server itself (an internal admin page). The weak version fetches any URL. The safe version
fetches only an allowed host, refuses a private or metadata address (SSRF), and does not follow a
redirect to a host that is not allowed.
"""

import ipaddress
import json
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from .data import WEB


class FetchDenied(Exception):
    code = "fetch_denied"

    def __init__(self, message: str, host: str = ""):
        super().__init__(message)
        self.host = host          # the host that was refused (after a redirect, the redirect's target)


@dataclass
class Page:
    status: int
    content_type: str
    body: str


def _hosts() -> dict:
    return json.loads((WEB / "hosts.json").read_text(encoding="utf-8"))


def _pages() -> dict:
    out = {}
    for line in (WEB / "pages.jsonl").read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        out[(p["host"], p["path"])] = p
    return out


def allowed_hosts(tenant: str) -> list[str]:
    return sorted(h for h, meta in _hosts().items() if tenant in meta.get("allowed_for", []))


def is_private(host: str) -> bool:
    meta = _hosts().get(host)
    address = meta["address"] if meta else host
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return host in ("localhost",) or host.endswith(".internal")


def _lookup(host: str, path: str) -> Page:
    pages = _pages()
    entry = pages.get((host, path)) or pages.get((host, "*"))
    if entry is None:
        return Page(404, "text/plain", "Not found.")
    if entry.get("status") == 302 and entry.get("redirect") == "query:to":
        return Page(302, "", "")   # a redirect; the caller reads the `to` query itself
    return Page(entry["status"], entry["content_type"], entry["body"])


def fetch_unsafe(url: str) -> tuple[Page, str]:
    """Fetch any URL, following one redirect (the weak version). Returns (page, final host)."""
    parsed = urlparse(url)
    host, path = parsed.hostname or "", parsed.path or "/"
    page = _lookup(host, path)
    if page.status == 302:
        to = parse_qs(parsed.query).get("to", [""])[0]
        return fetch_unsafe(to)
    return page, host


def fetch_sandboxed(url: str, tenant: str, _redirects: int = 1) -> tuple[Page, str]:
    """Fetch only from a host on the tenant's allow-list; refuse private/metadata hosts and bad redirects."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchDenied(f"{url}: only http and https are allowed.", parsed.hostname or "")
    host, path = parsed.hostname or "", parsed.path or "/"
    if is_private(host):
        raise FetchDenied(f"{host}: a private or internal address is never fetched.", host)
    if host not in allowed_hosts(tenant):
        raise FetchDenied(f"{host}: this host is not on the allow-list. Allowed: {', '.join(allowed_hosts(tenant))}.",
                          host)
    page = _lookup(host, path)
    if page.status == 302:
        to = parse_qs(parsed.query).get("to", [""])[0]
        if _redirects <= 0:
            raise FetchDenied("Too many redirects.", host)
        return fetch_sandboxed(to, tenant, _redirects - 1)   # the redirect target is checked again
    return page, host


def is_allowed_final(host: str, tenant: str) -> bool:
    return host in allowed_hosts(tenant) and not is_private(host)
