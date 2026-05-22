/**
 * popup.js の純関数ヘルパー。テスト容易化のため切り出し。
 * popup.js とテストの両方で読まれる前提なので、両環境で動く形に書く。
 */

function timeAgo(ts, now = null) {
  const nowSec = now !== null ? now : Date.now() / 1000;
  const diff = nowSec - ts;
  if (diff < 0) return "未来";
  if (diff < 60) return `${Math.floor(diff)}秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)}分前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
  return `${Math.floor(diff / 86400)}日前`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

/**
 * 一括投入用 textarea の入力を URL 配列にパース。
 *   - 各行を trim
 *   - 空行をスキップ
 *   - http:// または https:// で始まる行のみ採用
 */
function parseBulkUrls(text) {
  return String(text || "")
    .split("\n")
    .map(s => s.trim())
    .filter(s => /^https?:\/\//.test(s));
}

/**
 * ジョブ status を popup の CSS バッジクラス名に変換。
 */
function statusBadgeClass(status) {
  const valid = new Set(["queued", "running", "success", "error", "cancelled"]);
  return valid.has(status) ? status : "queued";
}

// Node (CommonJS) と Browser 両対応の export
if (typeof module !== "undefined" && module.exports) {
  module.exports = { timeAgo, escapeHtml, parseBulkUrls, statusBadgeClass };
}
