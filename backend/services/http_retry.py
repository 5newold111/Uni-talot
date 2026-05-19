"""
httpx 呼び出しに retry + 指数バックオフを足す軽量ヘルパー。

外部API (fal.ai, 画像CDN) は一時的な 5xx や接続エラーを返すことがあるため、
即失敗ではなく数回リトライしてからエラー伝播する。
"""

import asyncio
import logging
from collections.abc import Iterable

import httpx

logger = logging.getLogger(__name__)

# 5xx と 429 (Too Many Requests) はリトライ対象。4xx は基本的にクライアント側の問題なのでリトライしない。
DEFAULT_RETRY_STATUSES = (429, 500, 502, 503, 504)
DEFAULT_RETRY_EXCEPTIONS = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    retry_statuses: Iterable[int] = DEFAULT_RETRY_STATUSES,
    retry_exceptions: tuple = DEFAULT_RETRY_EXCEPTIONS,
    **kwargs,
) -> httpx.Response:
    """
    httpx.AsyncClient.request() を最大 max_attempts 回試行する。
    リトライ間は backoff_base ** attempt 秒待機 (1, 2, 4, ...)。
    すべて失敗したら最後の Response を返す (例外発生時は最後の例外を再送出)。
    """
    last_exc: Exception | None = None
    response: httpx.Response | None = None

    for attempt in range(max_attempts):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in retry_statuses:
                return response
            last_exc = None
        except retry_exceptions as e:
            last_exc = e
            response = None

        if attempt < max_attempts - 1:
            wait = backoff_base**attempt
            if last_exc:
                logger.warning(
                    f"HTTP {method} {url} 失敗 ({type(last_exc).__name__}: {last_exc}), "
                    f"{wait}s 待機 (試行 {attempt + 1}/{max_attempts})"
                )
            else:
                logger.warning(
                    f"HTTP {method} {url} → {response.status_code}, "
                    f"{wait}s 待機 (試行 {attempt + 1}/{max_attempts})"
                )
            await asyncio.sleep(wait)

    if response is not None:
        return response
    assert last_exc is not None
    raise last_exc
