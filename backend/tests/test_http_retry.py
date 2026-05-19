import httpx
import pytest
import respx

from services.http_retry import request_with_retry


@pytest.fixture(autouse=True)
def fast_sleep(monkeypatch):
    """テストでは指数バックオフを 0 秒にして高速化"""

    async def noop(_):
        return None

    monkeypatch.setattr("services.http_retry.asyncio.sleep", noop)


@respx.mock
async def test_returns_immediately_on_2xx():
    route = respx.get("https://example.com/ok").mock(return_value=httpx.Response(200))
    async with httpx.AsyncClient() as c:
        r = await request_with_retry(c, "GET", "https://example.com/ok")
    assert r.status_code == 200
    assert route.call_count == 1


@respx.mock
async def test_retries_5xx_then_succeeds():
    route = respx.get("https://example.com/flaky").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(502),
            httpx.Response(200),
        ]
    )
    async with httpx.AsyncClient() as c:
        r = await request_with_retry(c, "GET", "https://example.com/flaky", max_attempts=3)
    assert r.status_code == 200
    assert route.call_count == 3


@respx.mock
async def test_returns_last_response_when_all_retries_fail():
    route = respx.get("https://example.com/dead").mock(return_value=httpx.Response(500))
    async with httpx.AsyncClient() as c:
        r = await request_with_retry(c, "GET", "https://example.com/dead", max_attempts=3)
    assert r.status_code == 500
    assert route.call_count == 3


@respx.mock
async def test_does_not_retry_4xx():
    route = respx.get("https://example.com/notfound").mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as c:
        r = await request_with_retry(c, "GET", "https://example.com/notfound", max_attempts=3)
    assert r.status_code == 404
    assert route.call_count == 1


@respx.mock
async def test_retries_429():
    route = respx.get("https://example.com/rate").mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(200),
        ]
    )
    async with httpx.AsyncClient() as c:
        r = await request_with_retry(c, "GET", "https://example.com/rate", max_attempts=3)
    assert r.status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_retries_connection_errors_then_raises():
    route = respx.get("https://example.com/conn").mock(side_effect=httpx.ConnectError("refused"))
    async with httpx.AsyncClient() as c:
        with pytest.raises(httpx.ConnectError):
            await request_with_retry(c, "GET", "https://example.com/conn", max_attempts=3)
    assert route.call_count == 3
