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
 * 1 つの URL の文字列としての妥当性を判定。
 *   - http:// または https:// で始まる
 *   - URL コンストラクタでパース可能 (ホスト名がある)
 * フォーム入力のリアルタイム検証 / 単発タブの URL モードで使う。
 */
function isValidProductUrl(url) {
  const s = String(url || "").trim();
  if (!/^https?:\/\//.test(s)) return false;
  try {
    const u = new URL(s);
    return Boolean(u.hostname && u.hostname.length > 0);
  } catch (_) {
    return false;
  }
}

/**
 * URL のホスト名が、対応 EC サイトのいずれかに一致するか判定。
 * 拡張機能の host_permissions と整合させる。
 */
function isSupportedEcSite(url) {
  const SUPPORTED = [
    "nitori-net.jp",
    "ikea.com",
    "muji.com",
    "amazon.co.jp",
    "rakuten.co.jp",
    "low-ya.com",
    "cainz.com",
    "otsuka-kagu.co.jp",
  ];
  try {
    const u = new URL(url);
    return SUPPORTED.some(domain => u.hostname.includes(domain));
  } catch (_) {
    return false;
  }
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
  module.exports = {
    timeAgo,
    escapeHtml,
    parseBulkUrls,
    isValidProductUrl,
    isSupportedEcSite,
    statusBadgeClass,
  };
}
