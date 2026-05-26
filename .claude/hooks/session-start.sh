#!/bin/bash
# EC3D-Bridge SessionStart hook.
#
# Purpose:
#   1. Install Python + Node dependencies so tests / linters work on Claude Code on the web.
#   2. Inject a "handoff brief" (current branch, latest commit, top pending task,
#      pointer to docs/HANDOFF.md) into the new session's context.
#
# Idempotent: safe to run on every SessionStart (startup / resume / clear / compact).

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$PROJECT_DIR"

# Log install output to a file so it doesn't pollute the JSON we emit to stdout.
LOG="$PROJECT_DIR/.claude/hooks/session-start.log"
mkdir -p "$(dirname "$LOG")"
: > "$LOG"

{
  echo "=== SessionStart hook $(date -Iseconds) ==="
  echo "cwd: $PROJECT_DIR"
  echo "remote: ${CLAUDE_CODE_REMOTE:-false}"
} >> "$LOG"

install_backend() {
  if [ ! -f backend/requirements-dev.txt ]; then
    echo "no backend/requirements-dev.txt — skipping" >> "$LOG"
    return 0
  fi
  echo "--- pip install backend deps ---" >> "$LOG"
  # --quiet keeps output small; failures still surface because of set -e and the tee.
  pip install --disable-pip-version-check -q -r backend/requirements-dev.txt >> "$LOG" 2>&1
  # ruff is used by `just lint` / CI but is not in requirements-dev.txt.
  pip install --disable-pip-version-check -q ruff >> "$LOG" 2>&1
}

install_extension() {
  if [ ! -f extension/package.json ]; then
    echo "no extension/package.json — skipping" >> "$LOG"
    return 0
  fi
  echo "--- npm install extension deps ---" >> "$LOG"
  (cd extension && npm install --no-audit --no-fund --loglevel=error) >> "$LOG" 2>&1
}

# Run installers; if either fails, surface in the log but still emit context so
# Claude can see what went wrong.
INSTALL_STATUS="ok"
install_backend || INSTALL_STATUS="backend-failed"
install_extension || INSTALL_STATUS="${INSTALL_STATUS}+extension-failed"

# ----- Build the handoff brief that we inject into the new session -----

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
HEAD_COMMIT="$(git log -1 --pretty='%h %s' 2>/dev/null || echo unknown)"
DIRTY="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"

HANDOFF_SUMMARY=""
if [ -f docs/HANDOFF.md ]; then
  # First ~80 lines is enough to capture the "current status" + "top pending task"
  # sections; full file remains available via Read.
  HANDOFF_SUMMARY="$(sed -n '1,80p' docs/HANDOFF.md)"
fi

# Emit JSON for the Claude Code harness to consume.
# additionalContext is injected as a system reminder at session start.
python3 - "$BRANCH" "$HEAD_COMMIT" "$DIRTY" "$INSTALL_STATUS" "$HANDOFF_SUMMARY" <<'PY'
import json, sys
branch, head, dirty, install_status, handoff = sys.argv[1:6]

lines = [
    "=== EC3D-Bridge セッション引き継ぎブリーフ ===",
    f"ブランチ: {branch}",
    f"HEAD: {head}",
    f"未コミット変更: {dirty} 件",
    f"依存インストール: {install_status}",
    "",
    "🎯 最優先未対応タスク:",
    "  IKEA サイトでフローティングボタン (FAB) が表示されない不具合の修正。",
    "  方針は docs/HANDOFF.md の「2. 未対応の最優先タスク」セクション参照:",
    "    1) extension/scrapers/site_configs.js でホスト判定がヒットしたら",
    "       looksLikeProductPage() の img 閾値を緩める",
    "    2) MutationObserver で SPA ハイドレーション完了を待つ (最大 8s)",
    "    3) extension/tests/test_floating_button.mjs に IKEA 回帰テスト追加",
    "",
    "📝 開発ルール (絶対に外さない):",
    "  - 開発ブランチ: claude/ec3d-bridge-implementation-fv9ap",
    "  - .env / homestyler_storage_state.json / logs/ / output/ は commit 禁止",
    "  - SecretRedactor (logging filter) を撤去しない",
    "  - SSRF 防御 (url_safety.is_url_safe) を経由しない外部 fetch を追加しない",
    "  - CORS regex は chrome-extension:// と localhost のみ",
    "",
    "🧪 動作確認コマンド:",
    "  just test     # backend pytest + extension node --test",
    "  just lint     # ruff + manifest 検証",
    "",
]
if handoff:
    lines += ["", "----- docs/HANDOFF.md (冒頭 80 行) -----", handoff]

context = "\n".join(lines)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context,
    }
}))
PY
