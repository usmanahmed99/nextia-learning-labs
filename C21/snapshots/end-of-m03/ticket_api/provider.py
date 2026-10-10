"""The client of the AI provider (an OpenAI-compatible API).

On your computer the provider is the simulated one (`python -m simulator`, PROVIDER_URL
http://127.0.0.1:8300/v1). The same client works with a real provider: set PROVIDER_URL
and PROVIDER_API_KEY.

Every failure becomes one of four errors, so the caller can decide what to do:
- ProviderTimeout      no full answer within PROVIDER_TIMEOUT seconds
- ProviderRateLimited  HTTP 429: over the quota; `retry_after` says when to try again
- ProviderUnavailable  HTTP 5xx, or no connection
- ProviderRejected     another HTTP 4xx: the request itself is wrong (do not retry)
"""

import asyncio
import time

import httpx


class ProviderError(Exception):
    retryable = True

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ProviderTimeout(ProviderError):
    pass


class ProviderRateLimited(ProviderError):
    def __init__(self, message: str, retry_after: float | None):
        super().__init__(message, 429)
        self.retry_after = retry_after


class ProviderUnavailable(ProviderError):
    pass


class ProviderRejected(ProviderError):
    retryable = False


def _retry_after(response: httpx.Response) -> float | None:
    """Seconds to wait: retry-after-ms (more exact, if the provider sends it), else Retry-After."""
    for name, scale in (("retry-after-ms", 1000), ("retry-after", 1)):
        try:
            return float(response.headers[name]) / scale
        except (KeyError, ValueError):
            continue
    return None


def _check(response: httpx.Response) -> dict:
    if response.status_code == 200:
        return response.json()
    if response.status_code == 429:
        raise ProviderRateLimited("the provider's quota is used up", _retry_after(response))
    if response.status_code >= 500:
        raise ProviderUnavailable(
            f"the provider answered {response.status_code}", response.status_code
        )
    raise ProviderRejected(
        f"the provider refused the request ({response.status_code})", response.status_code
    )


def _headers(api_key: str | None) -> dict:
    if not api_key:
        return {}
    # Azure OpenAI reads api-key; most other providers read Authorization.
    return {"api-key": api_key, "Authorization": f"Bearer {api_key}"}


class Provider:
    """Sends chat and embedding requests. Use `call()` from a normal function (it waits), and
    `acall()` from an async function (it lets the server work on other requests meanwhile).

    max_concurrency limits the calls in flight from this process (acall only); the others
    wait their turn here, not at the provider."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_connections: int = 100,
        transport: httpx.BaseTransport | None = None,
        async_transport: httpx.AsyncBaseTransport | None = None,
        max_concurrency: int | None = None,
    ):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        limits = httpx.Limits(
            max_connections=max_connections, max_keepalive_connections=max_connections
        )
        # transport: the tests give a fake provider here; normally None (the network).
        self._sync = httpx.Client(
            base_url=self.base_url,
            headers=_headers(api_key),
            timeout=timeout,
            limits=limits,
            transport=transport,
        )
        self._async = httpx.AsyncClient(
            base_url=self.base_url,
            headers=_headers(api_key),
            timeout=timeout,
            limits=limits,
            transport=async_transport,
        )
        self.max_concurrency = max_concurrency
        self._slots = asyncio.Semaphore(max_concurrency) if max_concurrency else None

    def call(self, path: str, body: dict) -> tuple[dict, float]:
        """POST body to path ("chat/completions" or "embeddings"); the answer and the time in ms."""
        started = time.perf_counter()
        try:
            response = self._sync.post(path, json=body)
        except httpx.TimeoutException:
            raise ProviderTimeout(f"no answer within {self.timeout} seconds") from None
        except httpx.TransportError as error:
            raise ProviderUnavailable(f"no connection to the provider: {error}") from None
        return _check(response), (time.perf_counter() - started) * 1000

    async def acall(self, path: str, body: dict) -> tuple[dict, float]:
        """The same as call(), awaited. The time includes any wait for a free slot."""
        started = time.perf_counter()
        if self._slots is None:
            response = await self._apost(path, body)
        else:
            async with self._slots:
                response = await self._apost(path, body)
        return _check(response), (time.perf_counter() - started) * 1000

    async def _apost(self, path: str, body: dict) -> httpx.Response:
        try:
            return await self._async.post(path, json=body)
        except httpx.TimeoutException:
            raise ProviderTimeout(f"no answer within {self.timeout} seconds") from None
        except httpx.TransportError as error:
            raise ProviderUnavailable(f"no connection to the provider: {error}") from None

    def close(self) -> None:
        self._sync.close()

    async def aclose(self) -> None:
        await self._async.aclose()
