"""
3D生成キャッシュの単体テスト。Tripo API 呼び出しはモックする。
"""

import os

import httpx
import pytest
import respx

from services import model_generator
from services.model_generator import generate_3d_model


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(model_generator, "FAL_KEY", "test-key-not-placeholder")
    yield


@pytest.fixture
def fake_image(tmp_path):
    p = tmp_path / "img.jpg"
    p.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes-1234567890")
    return str(p)


@respx.mock
async def test_first_call_hits_api_and_writes_glb(fake_image):
    api_route = respx.post("https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d").mock(
        return_value=httpx.Response(200, json={"model_mesh": {"url": "https://cdn.fal/m.glb"}})
    )
    glb_route = respx.get("https://cdn.fal/m.glb").mock(
        return_value=httpx.Response(200, content=b"GLB-DATA")
    )

    out = await generate_3d_model(fake_image)
    assert os.path.exists(out)
    with open(out, "rb") as f:
        assert f.read() == b"GLB-DATA"
    assert api_route.call_count == 1
    assert glb_route.call_count == 1


@respx.mock
async def test_second_call_with_same_image_hits_cache(fake_image):
    api_route = respx.post("https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d").mock(
        return_value=httpx.Response(200, json={"model_mesh": {"url": "https://cdn.fal/m.glb"}})
    )
    respx.get("https://cdn.fal/m.glb").mock(return_value=httpx.Response(200, content=b"GLB-DATA"))

    out1 = await generate_3d_model(fake_image)
    out2 = await generate_3d_model(fake_image)
    assert out1 == out2  # 同じハッシュ → 同じパス
    assert api_route.call_count == 1  # 2回目は API を呼ばない


@respx.mock
async def test_different_image_different_cache_key(tmp_path):
    img1 = tmp_path / "a.jpg"
    img1.write_bytes(b"\xff\xd8" + b"AAA")
    img2 = tmp_path / "b.jpg"
    img2.write_bytes(b"\xff\xd8" + b"BBB")

    api_route = respx.post("https://fal.run/fal-ai/tripo3d/v2.5/image-to-3d").mock(
        side_effect=[
            httpx.Response(200, json={"model_mesh": {"url": "https://cdn.fal/1.glb"}}),
            httpx.Response(200, json={"model_mesh": {"url": "https://cdn.fal/2.glb"}}),
        ]
    )
    respx.get("https://cdn.fal/1.glb").mock(return_value=httpx.Response(200, content=b"G1"))
    respx.get("https://cdn.fal/2.glb").mock(return_value=httpx.Response(200, content=b"G2"))

    out1 = await generate_3d_model(str(img1))
    out2 = await generate_3d_model(str(img2))
    assert out1 != out2
    assert api_route.call_count == 2


async def test_missing_api_key_raises(fake_image, monkeypatch):
    from services.errors import ErrorCode, PipelineError

    monkeypatch.setattr(model_generator, "FAL_KEY", "")
    with pytest.raises(PipelineError) as exc:
        await generate_3d_model(fake_image)
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING


async def test_placeholder_api_key_raises(fake_image, monkeypatch):
    from services.errors import ErrorCode, PipelineError

    monkeypatch.setattr(model_generator, "FAL_KEY", "your_fal_api_key_here")
    with pytest.raises(PipelineError) as exc:
        await generate_3d_model(fake_image)
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING
