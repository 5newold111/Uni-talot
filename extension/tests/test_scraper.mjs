/**
 * Node 組み込みの test runner で動作するテスト。
 *   実行: node --test extension/tests/test_scraper.mjs
 *
 * scraper.js / site_configs.js は Chrome 拡張用にグローバル関数として書かれているので、
 * vm モジュールを使ってサンドボックス内で読み込み、JSON 経由で値を取り出して比較する
 * （cross-realm の Object/Array は deepStrictEqual で参照不一致になるため）。
 */
import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

function loadScraperContext() {
  const sandbox = {
    document: { querySelector: () => null, querySelectorAll: () => [] },
    window: { location: { hostname: "", href: "" } },
    chrome: { runtime: { onMessage: { addListener: () => {} } } },
  };
  vm.createContext(sandbox);
  vm.runInContext(readFileSync(join(ROOT, "scrapers/site_configs.js"), "utf8"), sandbox);
  vm.runInContext(readFileSync(join(ROOT, "content_scripts/scraper.js"), "utf8"), sandbox);
  return sandbox;
}

const ctx = loadScraperContext();

// cross-realm を跨ぐので JSON で値だけを比較する
const call = (fn, ...args) => JSON.parse(JSON.stringify(ctx[fn](...args)));

test("getSiteConfig matches nitori-net.jp", () => {
  const r = call("getSiteConfig", "www.nitori-net.jp");
  assert.equal(r.site, "nitori-net.jp");
  assert.match(r.config.name, /item_name/);
});

test("getSiteConfig matches subdomain hosts", () => {
  assert.equal(call("getSiteConfig", "shop.rakuten.co.jp").site, "rakuten.co.jp");
  assert.equal(call("getSiteConfig", "www.amazon.co.jp").site, "amazon.co.jp");
});

test("getSiteConfig matches new sites (low-ya, cainz, otsuka-kagu)", () => {
  assert.equal(call("getSiteConfig", "www.low-ya.com").site, "low-ya.com");
  assert.equal(call("getSiteConfig", "www.cainz.com").site, "cainz.com");
  assert.equal(call("getSiteConfig", "www.otsuka-kagu.co.jp").site, "otsuka-kagu.co.jp");
});

test("getSiteConfig falls back to default for unknown host", () => {
  const r = call("getSiteConfig", "unknown-store.example");
  assert.equal(r.site, "unknown");
  // default config の name セレクター
  assert.equal(r.config.name, "h1, [itemprop='name']");
});

test("parseDimensions: WxDxH cm pattern", () => {
  assert.deepEqual(call("parseDimensions", "W80×D40×H75cm"),
    { width_cm: 80, depth_cm: 40, height_cm: 75 });
});

test("parseDimensions: triple x in mm converts to cm", () => {
  assert.deepEqual(call("parseDimensions", "800×400×750mm"),
    { width_cm: 80, depth_cm: 40, height_cm: 75 });
});

test("parseDimensions: triple x in cm", () => {
  assert.deepEqual(call("parseDimensions", "80×40×75cm"),
    { width_cm: 80, depth_cm: 40, height_cm: 75 });
});

test("parseDimensions: 幅 奥行 高さ 個別パターン", () => {
  assert.deepEqual(call("parseDimensions", "幅: 120cm 奥行: 60cm 高さ: 72cm"),
    { width_cm: 120, depth_cm: 60, height_cm: 72 });
});

test("parseDimensions: 個別パターンの mm 表記", () => {
  assert.deepEqual(call("parseDimensions", "幅:1200mm 奥行:600mm 高さ:720mm"),
    { width_cm: 120, depth_cm: 60, height_cm: 72 });
});

test("parseDimensions: returns zeros when nothing matches", () => {
  assert.deepEqual(call("parseDimensions", "価格: 9,800円  色: ホワイト"),
    { width_cm: 0, depth_cm: 0, height_cm: 0 });
});

test("parseMaterials extracts known keywords", () => {
  const r = call("parseMaterials", "素材: 天然木 (オーク) フレーム + ファブリック");
  assert.deepEqual(r.sort(), ["オーク", "ファブリック", "天然木"].sort());
});

test("parseColors extracts both Japanese and English", () => {
  const r = call("parseColors", "Color: White / ホワイト");
  assert.ok(r.includes("ホワイト"));
  assert.ok(r.includes("white"));
});

test("parseColors returns empty for no match", () => {
  assert.deepEqual(call("parseColors", "商品コード: 12345"), []);
});
