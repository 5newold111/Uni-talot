"""
パイプライン全体で使う構造化エラー定義。

各サービスが PipelineError(code, message) を投げると、process.py が
これを補足してジョブの error_code と error 両方を記録する。フロントエンドは
error_code を読んで多言語メッセージ表示や復旧ガイダンスに活用できる。
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    IMAGE_DOWNLOAD_FAILED = "image_download_failed"
    IMAGE_TOO_SMALL = "image_too_small"
    MODEL_API_KEY_MISSING = "model_api_key_missing"
    MODEL_QUOTA_EXCEEDED = "model_quota_exceeded"
    MODEL_GENERATION_FAILED = "model_generation_failed"
    BLENDER_NOT_FOUND = "blender_not_found"
    SCALE_FAILED = "scale_failed"
    HOMESTYLER_AUTH_FAILED = "homestyler_auth_failed"
    HOMESTYLER_UI_CHANGED = "homestyler_ui_changed"
    UPLOAD_FAILED = "upload_failed"
    INTERNAL_ERROR = "internal_error"


# error_code → ユーザー向け推奨アクション。popup で表示する。
USER_GUIDANCE = {
    ErrorCode.INVALID_INPUT: "入力データの形式が不正です。商品ページを再読込してください。",
    ErrorCode.IMAGE_DOWNLOAD_FAILED: "商品画像のダウンロードに失敗しました。商品ページの画像URLを確認してください。",
    ErrorCode.IMAGE_TOO_SMALL: "画像の解像度が低すぎます (400px未満)。別の画像を選択してください。",
    ErrorCode.MODEL_API_KEY_MISSING: "FAL_API_KEY が未設定です。.env を確認してください。",
    ErrorCode.MODEL_QUOTA_EXCEEDED: "Tripo APIのクレジット残量を確認してください。",
    ErrorCode.MODEL_GENERATION_FAILED: "3Dモデル生成に失敗しました。しばらく待って再試行してください。",
    ErrorCode.BLENDER_NOT_FOUND: "Blender が見つかりません。.env の BLENDER_PATH を確認してください。",
    ErrorCode.SCALE_FAILED: "Blender でのスケール補正に失敗しました。",
    ErrorCode.HOMESTYLER_AUTH_FAILED: "Homestyler ログインに失敗しました。.env の認証情報を確認してください。",
    ErrorCode.HOMESTYLER_UI_CHANGED: "Homestyler の画面構成が変わった可能性があります。SELECTORS を再キャリブレーションしてください。",
    ErrorCode.UPLOAD_FAILED: "Homestyler へのアップロードに失敗しました。",
    ErrorCode.INTERNAL_ERROR: "予期しないエラーが発生しました。logs/app.log を確認してください。",
}


USER_GUIDANCE_EN = {
    ErrorCode.INVALID_INPUT: "Invalid input data. Please reload the product page and retry.",
    ErrorCode.IMAGE_DOWNLOAD_FAILED: (
        "Failed to download the product image. Check the image URL on the product page."
    ),
    ErrorCode.IMAGE_TOO_SMALL: "The image resolution is too low (under 400px). Choose another image.",
    ErrorCode.MODEL_API_KEY_MISSING: "FAL_API_KEY is not set. Check your .env file.",
    ErrorCode.MODEL_QUOTA_EXCEEDED: "Check your Tripo / fal.ai credit balance.",
    ErrorCode.MODEL_GENERATION_FAILED: "3D model generation failed. Please retry in a moment.",
    ErrorCode.BLENDER_NOT_FOUND: "Blender was not found. Check BLENDER_PATH in your .env.",
    ErrorCode.SCALE_FAILED: "Blender failed during scale correction.",
    ErrorCode.HOMESTYLER_AUTH_FAILED: (
        "Homestyler login failed. Check the credentials in your .env."
    ),
    ErrorCode.HOMESTYLER_UI_CHANGED: (
        "Homestyler's UI may have changed. Recalibrate SELECTORS in homestyler_bot.py."
    ),
    ErrorCode.UPLOAD_FAILED: "Upload to Homestyler failed.",
    ErrorCode.INTERNAL_ERROR: "Unexpected error. Inspect logs/app.log for details.",
}


def guidance_for(lang: str) -> dict:
    """Accept-Language の先頭値から JA/EN を選び、ErrorCode → メッセージ辞書を返す。"""
    if lang and lang.lower().startswith("en"):
        return USER_GUIDANCE_EN
    return USER_GUIDANCE


class PipelineError(Exception):
    """パイプライン内部で発生した構造化エラー。"""

    def __init__(self, code: ErrorCode, message: str, original: Exception | None = None):
        self.code = code
        self.message = message
        self.original = original
        super().__init__(f"[{code.value}] {message}")
