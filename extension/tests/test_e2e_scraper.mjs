/**
 * jsdom で fixture HTML を読み込み、extractProductData() を本物の DOM で実行する E2E テスト。
 *   実行: cd extension && npm test  または  node --test tests/test_e2e_scraper.mjs
 */
import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");

const SITE_CONFIGS_JS = readFileSync(join(ROOT, "scrapers/site_configs.js"), "utf8");
const SCRAPER_JS = readFileSync(join(ROOT, "content_scripts/scraper.js"), "utf8");

const CHROME_STUB = "var chrome = { runtime: { onMessage: { addListener: function(){} } } };\n";

function loadFixture(filename, hostname) {
  const html = readFileSync(join(__dirname, "fixtures", filename), "utf8");
  const dom = new JSDOM(html, { url: `https://${hostname}/products/123`, runScripts: "outside-only" });
  const window = dom.window;
  // 拡張ランタイムを stub したうえでスクリプトを評価
  window.eval(CHROME_STUB + SITE_CONFIGS_JS + "\n" + SCRAPER_JS);
  return JSON.parse(JSON.stringify(window.extractProductData()));
}

test("nitori fixture: extracts name, dimensions, materials, images", () => {
  const data = loadFixture("nitori.html", "www.nitori-net.jp");
  assert.equal(data.site, "nitori-net.jp");
  assert.equal(data.product_name, "ダイニングテーブル ノーチェ4 NA");
  assert.deepEqual(data.dimensions, { width_cm: 120, depth_cm: 75, height_cm: 72 });
  // ロゴ画像は除外される
  assert.ok(data.images.length >= 2);
  assert.ok(!data.images.some(i => i.url.includes("logo")));
  assert.equal(data.images[0].type, "front");
  assert.ok(data.materials.includes("天然木"));
  assert.ok(data.materials.includes("オーク"));
  assert.ok(data.materials.includes("MDF"));
  assert.ok(data.colors.includes("ナチュラル"));
});

test("ikea fixture: parses mm dimensions to cm", () => {
  const data = loadFixture("ikea.html", "www.ikea.com");
  assert.equal(data.site, "ikea.com");
  assert.equal(data.product_name, "MALM チェスト 6段");
  assert.deepEqual(data.dimensions, { width_cm: 80, depth_cm: 48, height_cm: 123 });
  assert.equal(data.images.length, 2);
});

test("amazon fixture: parses W×D×H cm pattern from product details", () => {
  const data = loadFixture("amazon.html", "www.amazon.co.jp");
  assert.equal(data.site, "amazon.co.jp");
  assert.ok(data.product_name.includes("サイドテーブル"));
  assert.deepEqual(data.dimensions, { width_cm: 50, depth_cm: 40, height_cm: 55 });
  assert.ok(data.materials.includes("ウォールナット"));
  assert.ok(data.materials.includes("スチール"));
});

test("source_url is captured from window.location", () => {
  const data = loadFixture("nitori.html", "www.nitori-net.jp");
  assert.ok(data.source_url.startsWith("https://www.nitori-net.jp/"));
});

test("category default is 家具", () => {
  const data = loadFixture("nitori.html", "www.nitori-net.jp");
  assert.equal(data.category, "家具");
});

test("low-ya.com fixture: extracts dimensions and materials", () => {
  const data = loadFixture("lowya.html", "www.low-ya.com");
  assert.equal(data.site, "low-ya.com");
  assert.equal(data.product_name, "ローソファ オットマン付 グレー");
  assert.deepEqual(data.dimensions, { width_cm: 180, depth_cm: 85, height_cm: 70 });
  assert.ok(data.materials.includes("ファブリック"));
  assert.ok(data.materials.includes("スチール"));
  assert.ok(data.colors.includes("グレー"));
});

test("low-ya.com matches subdomain", () => {
  const data = loadFixture("lowya.html", "shop.low-ya.com");
  assert.equal(data.site, "low-ya.com");
});
