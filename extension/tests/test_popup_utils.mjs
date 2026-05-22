/**
 * popup_utils.js の純関数テスト。
 *   実行: node --test extension/tests/test_popup_utils.mjs
 */
import { test } from "node:test";
import assert from "node:assert";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const utils = require("../popup/popup_utils.js");

// ===== timeAgo =====

test("timeAgo: 秒単位", () => {
  const now = 1000;
  assert.equal(utils.timeAgo(now - 0, now), "0秒前");
  assert.equal(utils.timeAgo(now - 30, now), "30秒前");
  assert.equal(utils.timeAgo(now - 59, now), "59秒前");
});

test("timeAgo: 分単位", () => {
  const now = 10000;
  assert.equal(utils.timeAgo(now - 60, now), "1分前");
  assert.equal(utils.timeAgo(now - 3599, now), "59分前");
});

test("timeAgo: 時間単位", () => {
  const now = 1_000_000;
  assert.equal(utils.timeAgo(now - 3600, now), "1時間前");
  assert.equal(utils.timeAgo(now - 86399, now), "23時間前");
});

test("timeAgo: 日単位", () => {
  const now = 10_000_000;
  assert.equal(utils.timeAgo(now - 86400, now), "1日前");
  assert.equal(utils.timeAgo(now - 86400 * 10, now), "10日前");
});

test("timeAgo: 未来時刻", () => {
  assert.equal(utils.timeAgo(2000, 1000), "未来");
});

// ===== escapeHtml =====

test("escapeHtml: 危険な文字を全てエスケープ", () => {
  assert.equal(utils.escapeHtml("<script>alert('xss')</script>"),
    "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;");
});

test("escapeHtml: ampersand を先頭に処理", () => {
  // & を最初にエスケープしないと &lt; → &amp;lt; のような二重エスケープが起きる
  assert.equal(utils.escapeHtml("a & b"), "a &amp; b");
  assert.equal(utils.escapeHtml("<a>"), "&lt;a&gt;");
});

test("escapeHtml: 引用符", () => {
  assert.equal(utils.escapeHtml('"hi"'), "&quot;hi&quot;");
  assert.equal(utils.escapeHtml("'hi'"), "&#39;hi&#39;");
});

test("escapeHtml: 通常文字は変更しない", () => {
  assert.equal(utils.escapeHtml("ダイニングテーブル ノーチェ4"),
    "ダイニングテーブル ノーチェ4");
});

test("escapeHtml: 非文字列は String() でキャスト", () => {
  assert.equal(utils.escapeHtml(42), "42");
  assert.equal(utils.escapeHtml(null), "null");
  assert.equal(utils.escapeHtml(undefined), "undefined");
});

// ===== parseBulkUrls =====

test("parseBulkUrls: 行区切りで URL を抽出", () => {
  const text = "https://example.com/a\nhttps://example.com/b\nhttps://example.com/c";
  assert.deepEqual(utils.parseBulkUrls(text), [
    "https://example.com/a",
    "https://example.com/b",
    "https://example.com/c",
  ]);
});

test("parseBulkUrls: 空行と空白を無視", () => {
  const text = "\n  https://example.com/a  \n\n  \nhttps://example.com/b\n";
  assert.deepEqual(utils.parseBulkUrls(text), [
    "https://example.com/a",
    "https://example.com/b",
  ]);
});

test("parseBulkUrls: http も https も両方許可", () => {
  const text = "http://localhost:3000/x\nhttps://nitori-net.jp/y";
  assert.equal(utils.parseBulkUrls(text).length, 2);
});

test("parseBulkUrls: javascript: / data: は弾く", () => {
  const text = "javascript:alert(1)\ndata:text/html,<x>\nfile:///etc/passwd\nhttps://ok.com/";
  assert.deepEqual(utils.parseBulkUrls(text), ["https://ok.com/"]);
});

test("parseBulkUrls: 空入力", () => {
  assert.deepEqual(utils.parseBulkUrls(""), []);
  assert.deepEqual(utils.parseBulkUrls(null), []);
  assert.deepEqual(utils.parseBulkUrls(undefined), []);
});

// ===== statusBadgeClass =====

test("statusBadgeClass: 既知の status はそのまま", () => {
  for (const s of ["queued", "running", "success", "error", "cancelled"]) {
    assert.equal(utils.statusBadgeClass(s), s);
  }
});

test("statusBadgeClass: 未知は queued にフォールバック", () => {
  assert.equal(utils.statusBadgeClass("anything-else"), "queued");
  assert.equal(utils.statusBadgeClass(""), "queued");
  assert.equal(utils.statusBadgeClass(null), "queued");
});
