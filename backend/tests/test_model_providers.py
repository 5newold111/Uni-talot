"""
ADR-006 で導入したプロバイダー抽象のテスト:
  - MODEL_PROVIDER env による切替
  - ColabTrellisProvider が multipart で画像を送信して GLB を受け取る
  - 各プロバイダーの認証 / 接続失敗時の構造化エラー
  - generate_3d_model のキャッシュがプロバイダー呼び出しを抑止
"""

import os

import httpx
import pytest
import respx

from services import model_generator, model_providers
from services.errors import ErrorCode, PipelineError

# ---- ファクトリー -----------------------------------------------------------


def test_factory_returns_tripo_by_default(monkeypatch):
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.setenv("FAL_API_KEY", "test-fal-key")
    provider = model_providers.get_provider()
    assert provider.name == "tripo"
    assert isinstance(provider, model_providers.TripoFalProvider)


def test_factory_returns_colab_trellis_when_selected(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "colab_trellis")
    monkeypatch.setenv("TRELLIS_COLAB_URL", "https://abc.ngrok-free.app")
    provider = model_providers.get_provider()
    assert provider.name == "colab_trellis"
    assert isinstance(provider, model_providers.ColabTrellisProvider)


def test_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "made_up_provider_xyz")
    with pytest.raises(PipelineError) as exc:
        model_providers.get_provider()
    assert exc.value.code == ErrorCode.INVALID_INPUT


def test_factory_case_insensitive(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "COLAB_TRELLIS")
    monkeypatch.setenv("TRELLIS_COLAB_URL", "https://abc.ngrok-free.app")
    provider = model_providers.get_provider()
    assert provider.name == "colab_trellis"


# ---- 認証/URL 未設定検出 --------------------------------------------------


def test_tripo_provider_rejects_missing_key():
    with pytest.raises(PipelineError) as exc:
        model_providers.TripoFalProvider(api_key="")
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING


def test_tripo_provider_rejects_placeholder_key():
    with pytest.raises(PipelineError) as exc:
        model_providers.TripoFalProvider(api_key="your_fal_api_key_here")
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING


def test_colab_trellis_provider_rejects_missing_url():
    with pytest.raises(PipelineError) as exc:
        model_providers.ColabTrellisProvider(base_url="")
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING


def test_colab_trellis_provider_rejects_placeholder_url():
    with pytest.raises(PipelineError) as exc:
        model_providers.ColabTrellisProvider(base_url="https://your-ngrok-url-here.ngrok-free.app")
    assert exc.value.code == ErrorCode.MODEL_API_KEY_MISSING


# ---- ColabTrellisProvider の HTTP 振る舞い ---------------------------------


@respx.mock
async def test_colab_provider_sends_multipart_and_returns_glb(tmp_path):
    img = tmp_path / "input.jpg"
    img.write_bytes(b"\xff\xd8" + b"jpeg-content-xx")
    glb_payload = b"glb-binary-data"

    route = respx.post("https://colab.example/generate").mock(
        return_value=httpx.Response(
            200, content=glb_payload, headers={"content-type": "model/gltf-binary"}
        )
    )
    provider = model_providers.ColabTrellisProvider(base_url="https://colab.example")
    result = await provider.generate(str(img))

    assert result == glb_payload
    assert route.call_count == 1
    # multipart で画像が送られていることを確認
    request = route.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b"jpeg-content-xx" in request.content


@respx.mock
async def test_colab_provider_detects_session_expired(tmp_path):
    """ngrok 切断 / Colab セッション切れの典型 (502/503/404) は明示的なメッセージで失敗"""
    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8" + b"jpg")
    respx.post("https://colab.example/generate").mock(
        return_value=httpx.Response(502, text="Bad Gateway")
    )
    provider = model_providers.ColabTrellisProvider(base_url="https://colab.example")
    with pytest.raises(PipelineError) as exc:
        await provider.generate(str(img))
    assert exc.value.code == ErrorCode.MODEL_GENERATION_FAILED
    assert "ngrok" in exc.value.message or "Colab" in exc.value.message


@respx.mock
async def test_colab_provider_other_5xx_is_generic_error(tmp_path):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8" + b"jpg")
    respx.post("https://colab.example/generate").mock(
        return_value=httpx.Response(500, text="internal")
    )
    provider = model_providers.ColabTrellisProvider(base_url="https://colab.example")
    with pytest.raises(PipelineError) as exc:
        await provider.generate(str(img))
    assert exc.value.code == ErrorCode.MODEL_GENERATION_FAILED


# ---- HuggingFaceSpaceProvider はスタブ -----------------------------------


async def test_hf_space_provider_is_stub(tmp_path):
    provider = model_providers.HuggingFaceSpaceProvider()
    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8")
    with pytest.raises(PipelineError) as exc:
        await provider.generate(str(img))
    assert exc.value.code == ErrorCode.MODEL_GENERATION_FAILED
    assert "未実装" in exc.value.message


# ---- generate_3d_model がキャッシュをチェック + プロバイダー委譲する ---------


@respx.mock
async def test_generate_3d_model_uses_provider_when_no_cache(tmp_path, monkeypatch):
    """キャッシュなしならプロバイダーが呼ばれ、戻り値が output/<hash>_raw.glb に保存される"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_PROVIDER", "colab_trellis")
    monkeypatch.setenv("TRELLIS_COLAB_URL", "https://colab.example")

    img = tmp_path / "in.jpg"
    img.write_bytes(b"\xff\xd8" + b"hello")
    glb = b"GLB-DATA-FROM-COLAB"

    route = respx.post("https://colab.example/generate").mock(
        return_value=httpx.Response(200, content=glb, headers={"content-type": "model/gltf-binary"})
    )

    save_path = await model_generator.generate_3d_model(str(img))
    assert os.path.exists(save_path)
    assert open(save_path, "rb").read() == glb
    assert route.call_count == 1


@respx.mock
async def test_generate_3d_model_skips_provider_when_cached(tmp_path, monkeypatch):
    """同じ画像 SHA-256 で 2 回目はプロバイダーを呼ばない"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_PROVIDER", "colab_trellis")
    monkeypatch.setenv("TRELLIS_COLAB_URL", "https://colab.example")

    img = tmp_path / "img.jpg"
    img.write_bytes(b"\xff\xd8" + b"same-content")
    glb = b"GLB-CACHED"

    route = respx.post("https://colab.example/generate").mock(
        return_value=httpx.Response(200, content=glb, headers={"content-type": "model/gltf-binary"})
    )

    path1 = await model_generator.generate_3d_model(str(img))
    path2 = await model_generator.generate_3d_model(str(img))
    assert path1 == path2  # 同じハッシュ → 同じパス
    assert route.call_count == 1  # 2 回目はプロバイダー呼ばない (キャッシュヒット)
