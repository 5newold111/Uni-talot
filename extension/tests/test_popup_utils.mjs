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

// ===== isValidProductUrl =====

test("isValidProductUrl: 有効な URL", () => {
  assert.equal(utils.isValidProductUrl("https://www.nitori-net.jp/ec/product/123/"), true);
  assert.equal(utils.isValidProductUrl("http://localhost:3000/x"), true);
  assert.equal(utils.isValidProductUrl("https://example.com/"), true);
});

test("isValidProductUrl: 空・空白", () => {
  assert.equal(utils.isValidProductUrl(""), false);
  assert.equal(utils.isValidProductUrl("   "), false);
  assert.equal(utils.isValidProductUrl(null), false);
  assert.equal(utils.isValidProductUrl(undefined), false);
});

test("isValidProductUrl: 非 http スキームを拒否", () => {
  assert.equal(utils.isValidProductUrl("javascript:alert(1)"), false);
  assert.equal(utils.isValidProductUrl("data:text/html,<x>"), false);
  assert.equal(utils.isValidProductUrl("file:///etc/passwd"), false);
  assert.equal(utils.isValidProductUrl("ftp://example.com/"), false);
});

test("isValidProductUrl: ホスト名がないものを拒否", () => {
  // "https://" だけはホストもパスも空 → パース失敗
  assert.equal(utils.isValidProductUrl("https://"), false);
  // 注: "http:///x" はブラウザ/Node の URL パーサーで hostname=x として
  // 正規化されるため、ここでの validity チェックは通る (実際の DNS で失敗する)
});

test("isValidProductUrl: 前後空白は trim される", () => {
  assert.equal(utils.isValidProductUrl("  https://example.com/  "), true);
});

// ===== isSupportedEcSite =====

test("isSupportedEcSite: 全対応サイトを認識", () => {
  const supported = [
    "https://www.nitori-net.jp/ec/product/1/",
    "https://www.ikea.com/jp/ja/p/x/",
    "https://www.muji.com/jp/x",
    "https://www.amazon.co.jp/dp/x",
    "https://item.rakuten.co.jp/shop/x/",
    "https://www.low-ya.com/products/x",
    "https://www.cainz.com/product/x",
    "https://www.otsuka-kagu.co.jp/x",
  ];
  for (const url of supported) {
    assert.equal(utils.isSupportedEcSite(url), true, `${url} should be supported`);
  }
});

test("isSupportedEcSite: サブドメイン違いも認識", () => {
  assert.equal(utils.isSupportedEcSite("https://shop.rakuten.co.jp/store/x"), true);
});

test("isSupportedEcSite: 対応外サイトは false", () => {
  assert.equal(utils.isSupportedEcSite("https://example.com/x"), false);
  assert.equal(utils.isSupportedEcSite("https://amazon.com/dp/x"), false);  // .co.jp ではない
});

test("isSupportedEcSite: 不正な URL は false", () => {
  assert.equal(utils.isSupportedEcSite("not-a-url"), false);
  assert.equal(utils.isSupportedEcSite(""), false);
  assert.equal(utils.isSupportedEcSite(null), false);
});
