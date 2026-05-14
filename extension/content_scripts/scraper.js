/**
 * ECページに注入されるコンテンツスクリプト。
 * Popupからのメッセージを受け取って商品情報を抽出し返す。
 * 注: site_configs.js は manifest.json の content_scripts で先に読み込まれる前提。
 */

function extractProductData() {
  const hostname = window.location.hostname;
  const { site, config } = getSiteConfig(hostname);

  const data = {
    product_name: "",
    source_url:   window.location.href,
    site,
    dimensions:   { width_cm: 0, depth_cm: 0, height_cm: 0 },
    colors:       [],
    materials:    [],
    images:       [],
    category:     "家具",
  };

  const nameEl = document.querySelector(config.name);
  data.product_name = nameEl ? nameEl.innerText.trim() : document.title.trim();

  const imageEls = document.querySelectorAll(config.images);
  const seenUrls = new Set();
  imageEls.forEach((img, index) => {
    const url = img.dataset.src || img.src || img.dataset.original || "";
    const cleanUrl = url.split("?")[0];
    if (url && !seenUrls.has(cleanUrl) && url.startsWith("http") && !url.includes("logo") && !url.includes("icon")) {
      seenUrls.add(cleanUrl);
      data.images.push({
        url,
        type: index === 0 ? "front" : "other"
      });
    }
  });

  const specEls = document.querySelectorAll(config.dimensions);
  const dimensionText = Array.from(specEls).map(el => el.innerText).join(" ");
  data.dimensions = parseDimensions(dimensionText);

  const materialEls = document.querySelectorAll(config.material);
  const materialText = Array.from(materialEls).map(el => el.innerText).join(" ");
  data.materials = parseMaterials(materialText);

  data.colors = parseColors(dimensionText + " " + materialText);

  return data;
}

/**
 * テキストから寸法を抽出する
 * 対応パターン: "幅80×奥行40×高さ75cm", "W80 D40 H75", "800mm×400mm×750mm"
 */
function parseDimensions(text) {
  const result = { width_cm: 0, depth_cm: 0, height_cm: 0 };

  const wdh = text.match(/[WwＷ幅]\s*([0-9.]+)\s*[×xX\s]*[DdＤ奥][行深]?\s*([0-9.]+)\s*[×xX\s]*[HhＨ高][さ]?\s*([0-9.]+)\s*(mm|cm|ｍｍ|ｃｍ)?/i);
  if (wdh) {
    const unit = (wdh[4] || "cm").toLowerCase().includes("mm") ? 10 : 1;
    result.width_cm  = parseFloat(wdh[1]) / unit;
    result.depth_cm  = parseFloat(wdh[2]) / unit;
    result.height_cm = parseFloat(wdh[3]) / unit;
    return result;
  }

  const triple = text.match(/([0-9.]+)\s*[×xX]\s*([0-9.]+)\s*[×xX]\s*([0-9.]+)\s*(mm|cm|ｍｍ|ｃｍ)/i);
  if (triple) {
    const unit = triple[4].toLowerCase().includes("mm") ? 10 : 1;
    result.width_cm  = parseFloat(triple[1]) / unit;
    result.depth_cm  = parseFloat(triple[2]) / unit;
    result.height_cm = parseFloat(triple[3]) / unit;
    return result;
  }

  const widthMatch  = text.match(/(?:幅|横|[Ww])[：:\s]*([0-9.]+)\s*(mm|cm)?/i);
  const depthMatch  = text.match(/(?:奥行|奥行き|[Dd])[：:\s]*([0-9.]+)\s*(mm|cm)?/i);
  const heightMatch = text.match(/(?:高さ|高[：:\s]*|[Hh])[：:\s]*([0-9.]+)\s*(mm|cm)?/i);

  if (widthMatch)  result.width_cm  = toCm(widthMatch[1],  widthMatch[2]);
  if (depthMatch)  result.depth_cm  = toCm(depthMatch[1],  depthMatch[2]);
  if (heightMatch) result.height_cm = toCm(heightMatch[1], heightMatch[2]);

  return result;
}

function toCm(value, unit) {
  const n = parseFloat(value);
  return unit && unit.toLowerCase().includes("mm") ? n / 10 : n;
}

function parseMaterials(text) {
  const keywords = ["天然木", "ウォールナット", "オーク", "パイン", "合板", "MDF", "スチール",
                    "アルミ", "ファブリック", "レザー", "ポリエステル", "綿", "麻", "竹", "籐"];
  return keywords.filter(k => text.includes(k));
}

function parseColors(text) {
  const colorWords = ["ホワイト", "ブラック", "ナチュラル", "ブラウン", "グレー", "ベージュ",
                      "ウォールナット", "オーク", "ライトブラウン", "ダークブラウン",
                      "white", "black", "natural", "brown", "gray", "beige"];
  return colorWords.filter(c => text.toLowerCase().includes(c.toLowerCase()));
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "EXTRACT_PRODUCT") {
    try {
      const data = extractProductData();
      sendResponse({ success: true, data });
    } catch (e) {
      sendResponse({ success: false, error: e.message });
    }
  }
  return true;
});
