/**
 * floating_button.js (ページ内 FAB) の動作テスト。
 * jsdom + chrome API モックで EC ページに注入される挙動を検証。
 */
import { test } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM } from "jsdom";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const SCRAPER_JS = readFileSync(join(ROOT, "content_scripts/scraper.js"), "utf8");
const SITE_CONFIGS_JS = readFileSync(join(ROOT, "scrapers/site_configs.js"), "utf8");
const FAB_JS = readFileSync(join(ROOT, "content_scripts/floating_button.js"), "utf8");

// 商品ページっぽい最小 HTML (h1 と img >= 3)
const PRODUCT_PAGE_HTML = `
<!DOCTYPE html>
<html><head><title>テスト商品</title></head>
<body>
  <h1 class="item_name">テストチェア</h1>
  <div class="item-image">
    <img src="https://example.com/img1.jpg">
    <img src="https://example.com/img2.jpg">
    <img src="https://example.com/img3.jpg">
  </div>
  <table class="spec-table"><tr><td>幅60cm × 奥行60cm × 高さ80cm</td></tr></table>
</body></html>`;

// 商品ページでないページ (h1 はあるが画像が少ない)
const NON_PRODUCT_PAGE_HTML = `
<!DOCTYPE html><html><head><title>トップ</title></head>
<body><h1>サイトトップ</h1></body></html>`;

const CHROME_STUB = (storage = {}) => `
  var chrome = {
    runtime: { onMessage: { addListener: function(){} } },
    storage: {
      local: {
        _data: ${JSON.stringify(storage)},
        get: function(keys, cb) {
          var out = {};
          if (typeof keys === 'string') keys = [keys];
          if (Array.isArray(keys)) {
            keys.forEach(function(k){ out[k] = chrome.storage.local._data[k]; });
          } else if (keys === null) {
            out = chrome.storage.local._data;
          }
          cb(out);
        },
        set: function(obj, cb) {
          Object.keys(obj).forEach(function(k){ chrome.storage.local._data[k] = obj[k]; });
          if (cb) cb();
        },
        remove: function(keys, cb) {
          if (!Array.isArray(keys)) keys = [keys];
          keys.forEach(function(k){ delete chrome.storage.local._data[k]; });
          if (cb) cb();
        },
      }
    }
  };
`;

function loadFabWithProductPage(html, hostname = "www.nitori-net.jp", storage = {}) {
  const dom = new JSDOM(html, {
    url: `https://${hostname}/products/1`,
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  dom.window.eval(CHROME_STUB(storage) + SITE_CONFIGS_JS + "\n" + SCRAPER_JS + "\n" + FAB_JS);
  // JSDOM の readyState は "loading" のまま動かないので DOMContentLoaded を手動で fire
  dom.window.document.dispatchEvent(new dom.window.Event("DOMContentLoaded"));
  return dom;
}

// ===== 注入の基本動作 =====

test("FAB: 商品ページなら #ec3d-bridge-fab-root が DOM に注入される", () => {
  const dom = loadFabWithProductPage(PRODUCT_PAGE_HTML);
  const root = dom.window.document.getElementById("ec3d-bridge-fab-root");
  assert.ok(root, "FAB ルート要素が見つからない");
  // Shadow DOM 内に .fab があるはず
  assert.ok(root.shadowRoot, "Shadow DOM が作られていない");
  const fab = root.shadowRoot.querySelector(".fab");
  assert.ok(fab, ".fab 要素が Shadow DOM 内にない");
});

test("FAB: 商品ページでなければ注入されない (h1 のみ、img 少)", () => {
  const dom = loadFabWithProductPage(NON_PRODUCT_PAGE_HTML);
  const root = dom.window.document.getElementById("ec3d-bridge-fab-root");
  assert.equal(root, null, "商品ページでないのに FAB が注入された");
});

test("FAB: extractProductData が window に公開される (FAB から呼べる)", () => {
  const dom = loadFabWithProductPage(PRODUCT_PAGE_HTML);
  assert.equal(typeof dom.window.extractProductData, "function");
  const data = dom.window.extractProductData();
  assert.equal(data.product_name, "テストチェア");
});

// ===== 設定による無効化 =====

test("FAB: ec3d_fab_disabled が true なら注入されない", () => {
  const dom = loadFabWithProductPage(
    PRODUCT_PAGE_HTML, "www.nitori-net.jp", { ec3d_fab_disabled: true }
  );
  const root = dom.window.document.getElementById("ec3d-bridge-fab-root");
  assert.equal(root, null, "無効化フラグが効いていない");
});

test("FAB: ページ単位の dismissed フラグが効く", () => {
  const pageKey = "ec3d_fab_dismissed:www.nitori-net.jp/products/1";
  const dom = loadFabWithProductPage(
    PRODUCT_PAGE_HTML, "www.nitori-net.jp", { [pageKey]: true }
  );
  const root = dom.window.document.getElementById("ec3d-bridge-fab-root");
  assert.equal(root, null, "ページ単位 dismiss が効いていない");
});

// ===== 二重注入防止 =====

test("FAB: 同じスクリプトを 2 回 eval しても 1 つしか注入されない", () => {
  const dom = loadFabWithProductPage(PRODUCT_PAGE_HTML);
  // もう一度同じ FAB スクリプトを実行
  dom.window.eval(FAB_JS);
  const roots = dom.window.document.querySelectorAll("#ec3d-bridge-fab-root");
  assert.equal(roots.length, 1);
});

// ===== Shadow DOM のスタイル隔離 =====

test("FAB: Shadow DOM 内 .fab のテキストにラベルが含まれる", () => {
  const dom = loadFabWithProductPage(PRODUCT_PAGE_HTML);
  const root = dom.window.document.getElementById("ec3d-bridge-fab-root");
  const fab = root.shadowRoot.querySelector(".fab");
  assert.ok(fab.textContent.includes("3D化"), `期待ラベル '3D化' が含まれない: ${fab.textContent}`);
  // 閉じるボタンも存在
  assert.ok(root.shadowRoot.querySelector(".close"), "× ボタンがない");
});

// ===== マニフェスト整合性 =====

test("manifest.json の content_scripts に floating_button.js が含まれる", () => {
  const manifest = JSON.parse(readFileSync(join(ROOT, "manifest.json"), "utf8"));
  const cs = manifest.content_scripts[0].js;
  assert.ok(
    cs.includes("content_scripts/floating_button.js"),
    `manifest に floating_button.js が含まれない: ${JSON.stringify(cs)}`
  );
  // 依存関係 (scraper.js が先) も保たれているか
  const fabIdx = cs.indexOf("content_scripts/floating_button.js");
  const scraperIdx = cs.indexOf("content_scripts/scraper.js");
  assert.ok(scraperIdx < fabIdx, "scraper.js が floating_button.js より前にない");
});
