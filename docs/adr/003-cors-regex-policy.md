# ADR-003: CORS は chrome-extension と localhost のみ regex 許可

- ステータス: 採用
- 日付: 2026-05-15

## 背景

初期実装は `allow_origins=["*"]` で開発を進めていたが、これだと開発者の PC で動いているバックエンドに、ブラウザで開いている**任意のWebサイト**から fetch リクエストが届く。悪意ある Web ページが localhost:3000 を叩いて勝手にジョブを投入できる状態だった。

## 決定

`allow_origin_regex` を使い以下のみ許可:

```
^(chrome-extension://[a-zA-Z0-9_-]+|https?://localhost(:\d+)?|https?://127\.0\.0\.1(:\d+)?)$
```

- `chrome-extension://<id>` — 拡張機能本体
- `http(s)://localhost(:port)?` — ローカル開発、API テスト
- `http(s)://127.0.0.1(:port)?` — 同上

許可メソッドも `["*"]` から `["GET", "POST", "OPTIONS"]` に絞る。

## 結果

**利点:**
- 任意の悪意ある Web ページから API を叩けなくなる
- chrome-extension ID は拡張機能配布前後で変わるので、ID を ALLOWLIST にハードコードできない問題を regex で解決
- preflight (OPTIONS) は許可・拒否がレスポンスヘッダで観測可能

**トレードオフ:**
- 開発時に別マシンから叩く場合は localhost トンネル必須
- regex マッチでのオリジン判定はホワイトリスト方式より柔軟だが、誤マッチのリスクは残る (テストでカバー)

## 補完策

CORS は同一オリジンポリシーに従う**ブラウザのみ**のガードである。`curl` や `httpie` など非ブラウザクライアントは CORS を無視できるため、強い保護にはならない。本番運用前に [ADR-005 の構造化エラー](./005-structured-error-codes.md) と併せて、`EC3D_API_KEY` による認証を有効化することを強く推奨。
