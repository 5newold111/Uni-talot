# セキュリティ評価レポート

最終監査日: 2026-05-22 (v2.1.0 時点)

このドキュメントは、現状の EC3D-Bridge がどのような機微情報を扱い、どこに格納し、どんな脅威モデルに耐えるか・耐えないかを率直に評価したものです。

## TL;DR

- **想定運用**: 個人の開発機で動かす単一ユーザー向けツール。インターネットに露出させない前提
- **危険度**: 適切に扱えば**個人プロジェクトとして許容範囲**。ただし要注意ポイントが複数あり (下記)
- **本番化 / マルチユーザー化**: 別途対策必須 (Postgres移行 / OAuth / TLS / WAF / etc.)

## 取り扱う機微情報

| 種類 | 保存場所 | 機密度 | 漏洩時の影響 |
|---|---|---|---|
| `FAL_API_KEY` | `.env` (gitignore済) / `os.environ` | **高** | Tripo クレジット盗用 (課金被害) |
| `HOMESTYLER_EMAIL/PASSWORD` | `.env` / `os.environ` | **高** | Homestyler アカウント乗っ取り |
| `homestyler_storage_state.json` | プロジェクト直下 (gitignore済) | **高** | セッション Cookie = 実質ログイン認証 |
| `EC3D_API_KEY` | `.env` / クライアント側 `chrome.storage.local` | 中 | バックエンド API アクセス |
| `jobs.db` (SQLite) | プロジェクト直下 (gitignore済) | 低-中 | 商品名・URL・寸法など (PII 性は限定的) |
| `output/*.glb` | プロジェクト直下 (gitignore済) | 低 | 3D モデルファイル (公開画像から生成) |
| `logs/app.log` | プロジェクト直下 (gitignore済) | 中 | ジョブ実行記録 (シークレットマスキング適用) |
| `logs/error_*.{png,html}` | プロジェクト直下 (gitignore済) | **高** | Homestyler 失敗時の DOM/スクショ → アカウント情報を含み得る |

## 脅威モデルと対策

### 🛡️ 防御済み

#### 1. シークレットの誤コミット
- **対策**: `.env`, `homestyler_storage_state.json`, `homestyler_selectors.json`, `homestyler_*.json`, `logs/`, `output/`, `*.db` を `backend/.gitignore` に登録
- **検証**: `tests/test_security.py::test_critical_files_are_gitignored`
- **CI**: pre-commit に `detect-private-key` フック導入済み

#### 2. ログへの機密値漏洩
- **対策**: `SecretRedactor` ロギングフィルターが `FAL_API_KEY` / `HOMESTYLER_PASSWORD` / `EC3D_API_KEY` の生値を自動マスク (`<REDACTED:NAME>`)
- **設計判断**: 「漏らさないコードを書く」が第一原則だが、最終防衛線として動かす
- **限界**: プレースホルダ値 (`your_*_here`) や 8 文字未満の値はマスクしない (誤検知防止)

#### 3. SSRF (Server-Side Request Forgery)
- **脅威**: 悪意ある EC ページが商品画像 URL に `http://127.0.0.1:6379/` や `http://169.254.169.254/` (AWS IMDS) を含めるとバックエンドが内部リソースへリクエスト
- **対策**: `services/url_safety.py` の `is_url_safe()` が以下を遮断:
  - http/https 以外のスキーム (`file://`, `javascript:`, `ftp://`)
  - private IP 範囲 (10/8, 172.16/12, 192.168/16)
  - loopback (127/8, ::1)
  - link-local (169.254/16, fe80::/10) — AWS/GCP メタデータエンドポイント含む
  - 予約済み / 解決不能ドメイン
- **検証**: 11 件のパラメトリックテスト

#### 4. CORS バイパス
- **対策**: `chrome-extension://<id>` と `localhost`/`127.0.0.1` のみ regex 許可
- **検証**: 12 件の CORS テスト (許可/拒否/preflight)
- **限界**: CORS はブラウザ限定。curl 等の非ブラウザクライアントには無効

#### 5. シェルインジェクション
- **対策**: `subprocess.run` で `shell=False` (デフォルト) を使用、引数は list 形式で渡す
- **Blender 引数**: 寸法は Pydantic で `0 <= x <= 1000` の数値範囲チェック済み

#### 6. パストラバーサル (`/output/*`)
- **対策**: FastAPI の `StaticFiles` が `../` を自動的に拒否

#### 7. レート制限 / DoS
- **対策**: `RateLimitMiddleware` でジョブ投入を IP あたり 10バースト/0.5req/sec に制限
- **X-Forwarded-For** 対応 (リバプロ越し)

#### 8. 入力バリデーション
- **対策**: Pydantic v2 で `HttpUrl`, `min_length`, `max_length`, 寸法範囲 (0〜1000cm), 画像枚数 (1〜50) を強制
- **検証**: 12 件の validation テスト

#### 9. エラーメッセージからの情報漏洩
- **対策**: Tripo API のエラーレスポンス本文 (`response.text`) は `PipelineError.message` に含めない。ステータスコードのみ。詳細は logs/ にのみ書く
- **検証**: `test_tripo_error_message_does_not_leak_response_body`

### ⚠️ 既知のリスク (運用で対応)

#### 1. `EC3D_API_KEY` がデフォルト空 = 認証なし
- **状況**: env で設定するまで誰でも `localhost:3000` の API を叩ける
- **想定運用**: 個人 PC のローカル限定なので CORS で 99% 守られる
- **本番化する場合**: `EC3D_API_KEY` を必ず設定 + nginx 等の前段認証

#### 2. `logs/error_*.{png,html}` に PII が混入し得る
- **問題**: Homestyler 失敗時に DOM をフルダンプするので、ログイン中のメールアドレス・登録情報・他の商品情報などが含まれ得る
- **緩和策**:
  - `.gitignore` で除外済み (誤コミット防止)
  - `logs/` 全体がローカル限定アクセス
- **追加緩和**: 重要なら定期削除 cron を仕掛ける (`find logs/ -mtime +7 -delete`)

#### 3. Homestyler 認証情報の平文保存
- **問題**: `.env` の `HOMESTYLER_PASSWORD` と `homestyler_storage_state.json` は平文
- **緩和策**:
  - `storage_state` 方式を推奨 (パスワード自体を入力しない)
  - OS のキーチェーン連携 (Keychain / DPAPI / libsecret) は将来課題
- **本番化**: HashiCorp Vault / AWS Secrets Manager 等を使うべき

#### 4. Chrome 拡張機能の広い `host_permissions`
- **問題**: 8 サイトすべてに対し DOM 読み取り可能 (スクレイピングのため必要)
- **緩和策**: `activeTab` 併用で実行時のみ展開、コンテンツスクリプトは `EXTRACT_PRODUCT` メッセージにのみ応答
- **第三者監査**: extension が外部に通信するのは `http://localhost:3000` のみ (manifest で制限)

#### 5. SQLite シングルプロセス
- **問題**: 複数 uvicorn worker やマルチサーバー構成では競合
- **緩和策**: 単一ワーカー前提で運用
- **本番化**: Postgres 移行 (スキーマ互換あり)

#### 6. キャンセル不可能な Tripo API 呼び出し
- **問題**: 3D 生成は 30〜120 秒かかり、その間キャンセルできない (HTTP リクエスト中断不可)
- **影響**: クレジットの無駄消費は防げない
- **緩和策**: 投入前に画像キャッシュチェック (SHA-256)

### 🟡 想定外運用での注意

| シナリオ | 危険度 | 推奨対応 |
|---|---|---|
| インターネットに公開 (uvicorn を 0.0.0.0 で外部公開) | **高** | やめる。nginx/Caddy で TLS+認証+WAF を被せる |
| マルチユーザー利用 | 高 | Postgres + OAuth + ユーザー隔離が必要 |
| CI/CD パイプラインで動かす | 中 | secrets を GitHub Actions Secrets / OIDC で渡す |
| 共有 Docker ホストで動かす | 中 | volume の権限を 700、 `EC3D_API_KEY` 必須 |
| 公開 Chrome ストアに公開 | 中 | extension に host_permissions の最小化、`localhost` 強制 |

## 依存性のセキュリティ

| 種類 | 管理状況 |
|---|---|
| Python パッケージ | `requirements.txt` で固定バージョン pinning |
| Node パッケージ | `package-lock.json` で固定 |
| Blender | apt 経由 (システム更新で追従) |
| 脆弱性スキャン | ❌ Dependabot / Snyk 未設定 (将来課題) |
| SBOM | ❌ 未生成 (将来課題) |

推奨: `.github/workflows/test.yml` に `pip-audit` / `npm audit` を追加。

## サプライチェーン

| ベクター | 状況 |
|---|---|
| `pip install` 経由のマルウェア | 全パッケージ固定バージョン、`requirements*.txt` を CI で再現可能ビルド |
| `npm install` 経由 | `package-lock.json` で固定 |
| pre-commit フック | 公式リポジトリ (`pre-commit/pre-commit-hooks`, `astral-sh/ruff-pre-commit`) を使用 |

## プライバシー / 法令観点

### 個人情報の取り扱い
- 拡張機能はユーザーが開いた商品ページの DOM を読み取り、商品情報のみを抽出してバックエンドに送信
- ユーザーの閲覧履歴・他のタブの情報は読まない
- すべての処理はローカル PC で完結 (FAL API と Homestyler を除く)

### 第三者サービスへの送信
- **fal.ai (Tripo)**: 商品画像をアップロード → 3D モデルを取得。**画像は fal.ai のサーバーに送られる** (個人情報なら注意、商品画像なら通常問題なし)
- **Homestyler**: GLB ファイル + 商品名・寸法を送信
- **EC サイト**: スクレイピング先 (公開ページのみ)

### GDPR / 個人情報保護法
- ユーザー (ツール所有者) のデータのみを扱い、第三者の個人情報は扱わない
- 商品情報は EC サイトで公開済みのデータ

## 推奨運用チェックリスト

ユーザーが本番運用する前に確認すべき項目:

- [ ] `.env` をコミットしていない (`git ls-files | grep .env` が空)
- [ ] `homestyler_storage_state.json` をコミットしていない
- [ ] `EC3D_API_KEY` を設定した (デフォルト空 = 認証なし)
- [ ] バックエンドを `127.0.0.1` バインドで起動 (`0.0.0.0` ではない)
- [ ] Docker で動かす場合は `volume` の権限を 700 に
- [ ] `logs/` を定期削除 (PII 含み得る)
- [ ] FAL_API_KEY の利用上限を fal.ai 管理画面で設定 (誤操作時の課金保護)
- [ ] Homestyler に普段使いと別アカウントを用意 (BAN リスク隔離)
- [ ] `pre-commit install` 実行 (`detect-private-key` フック)

## 報告窓口

セキュリティ問題を発見した場合は GitHub Issues ではなく、リポジトリ管理者に直接連絡してください。

## 検証カバレッジ

`backend/tests/test_security.py` に 18 件のセキュリティ専用テストがあり、以下を自動で検証:

| カテゴリ | テスト数 |
|---|---|
| SSRF 防御 (URL 検査) | 11 |
| シークレットマスキング | 4 |
| エラーメッセージ漏洩防止 | 1 |
| .gitignore 整合性 | 1 |
| image_downloader の安全URL検査 | 1 |

総合カバレッジ 93%、セキュリティクリティカルパスは 100% カバー。
