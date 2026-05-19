import os
from io import BytesIO

import httpx
import pytest
import respx
from PIL import Image

from services.errors import ErrorCode, PipelineError
from services.image_downloader import download_main_image


def _make_jpeg_bytes(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), (200, 100, 50))
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield


async def test_no_images_raises():
    with pytest.raises(PipelineError) as exc:
        await download_main_image([])
    assert exc.value.code == ErrorCode.IMAGE_DOWNLOAD_FAILED


async def test_skips_non_http_urls():
    images = [{"url": "data:image/png;base64,xxx", "type": "front"}]
    with pytest.raises(PipelineError):
        await download_main_image(images)


@respx.mock
async def test_skips_low_resolution_then_uses_next():
    small_url = "https://example.com/small.jpg"
    big_url = "https://example.com/big.jpg"
    respx.get(small_url).mock(return_value=httpx.Response(200, content=_make_jpeg_bytes(100, 100)))
    respx.get(big_url).mock(return_value=httpx.Response(200, content=_make_jpeg_bytes(800, 600)))

    saved = await download_main_image(
        [
            {"url": small_url, "type": "front"},
            {"url": big_url, "type": "other"},
        ]
    )
    assert os.path.exists(saved)
    assert saved.endswith("_input.jpg")
    # 大きい方が保存されている
    img = Image.open(saved)
    assert (img.width, img.height) == (800, 600)


@respx.mock
async def test_front_image_is_preferred():
    front = "https://example.com/front.jpg"
    side = "https://example.com/side.jpg"
    respx.get(front).mock(return_value=httpx.Response(200, content=_make_jpeg_bytes(800, 800)))
    respx.get(side).mock(return_value=httpx.Response(200, content=_make_jpeg_bytes(800, 800)))

    # 入力は side が先でも front が優先される
    saved = await download_main_image(
        [
            {"url": side, "type": "side"},
            {"url": front, "type": "front"},
        ]
    )
    # respx は呼び出し履歴を持つので front が実際にダウンロードされたことを確認
    assert respx.calls[0].request.url == front
    assert os.path.exists(saved)


@respx.mock
async def test_http_error_is_skipped():
    bad = "https://example.com/bad.jpg"
    good = "https://example.com/good.jpg"
    respx.get(bad).mock(return_value=httpx.Response(404))
    respx.get(good).mock(return_value=httpx.Response(200, content=_make_jpeg_bytes(800, 800)))
    saved = await download_main_image(
        [
            {"url": bad, "type": "front"},
            {"url": good, "type": "other"},
        ]
    )
    assert os.path.exists(saved)
