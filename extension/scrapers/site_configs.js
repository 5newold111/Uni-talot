/**
 * サイト別セレクター設定
 * 各サイトのHTML構造が変わった場合はここを更新する
 */
const SITE_CONFIGS = {

  "nitori-net.jp": {
    name:        "h1.item_name, .pdct-name h1, h1[class*='name']",
    images:      ".item-image img, .pdct-image img, #js-productMainImage img",
    description: ".item-desc, .pdct-desc",
    dimensions:  ".spec-table td, .pdct-spec td, table.spec td",
    material:    ".spec-table, .pdct-spec",
  },

  "ikea.com": {
    name:        "[data-testid='product-title'], h1.pip-header-section__title",
    images:      ".pip-media-grid img, [data-testid='product-image'] img",
    description: ".pip-product-details, [data-testid='product-description']",
    dimensions:  "[data-testid='product-dimensions'], .pip-product-dimensions",
    material:    "[data-testid='product-details']",
  },

  "muji.com": {
    name:        ".product-name h1, h1.item-name",
    images:      ".product-image-main img, .item-image img",
    description: ".product-description, .item-description",
    dimensions:  ".product-spec table td, .spec-list li",
    material:    ".product-material, .item-material",
  },

  "amazon.co.jp": {
    name:        "#productTitle",
    images:      "#imgTagWrapperId img, #imageBlock img, #altImages img",
    description: "#productDescription, #feature-bullets li",
    dimensions:  "#productDetails_techSpec_section_1 td, #detailBulletsWrapper_feature_div span",
    material:    "#productDetails_techSpec_section_1, #feature-bullets",
  },

  "rakuten.co.jp": {
    name:        "h1, .item_name, [itemprop='name']",
    images:      ".rakutenLimitedId_ImageMain1-1 img, #rakuten-ichiba-item-image img, .item_photo img",
    description: ".item_desc, #item_description, [itemprop='description']",
    dimensions:  "table td, .spec td, .item_spec td",
    material:    "table, .spec, .item_spec",
  },

  "low-ya.com": {
    name:        "h1.product-name, h1.item-title, h1",
    images:      ".product-gallery img, .item-image-main img, [class*='product-image'] img",
    description: ".product-description, .item-description, .item-text",
    dimensions:  ".product-spec td, .item-spec td, .spec-table td",
    material:    ".product-spec, .item-spec, .spec-table",
  },

  "cainz.com": {
    name:        "h1.product-name, .product-title h1, h1",
    images:      ".product-main-image img, .product-images img, .item-photo img",
    description: ".product-description, .product-detail-text",
    dimensions:  ".product-spec td, .spec-table td, .product-detail-table td",
    material:    ".product-spec, .spec-table, .product-detail-table",
  },

  "otsuka-kagu.co.jp": {
    name:        "h1.item-name, .product-title, h1",
    images:      ".item-main-image img, .product-photo img, .gallery-main img",
    description: ".item-description, .product-detail",
    dimensions:  ".item-spec td, .spec-list td, table.spec td",
    material:    ".item-spec, .spec-list, table.spec",
  },

  "default": {
    name:        "h1, [itemprop='name']",
    images:      "[itemprop='image'] img, .product-image img, main img",
    description: "[itemprop='description'], .product-description, .item-description",
    dimensions:  "table td, .spec td",
    material:    "table, .spec",
  }
};

function getSiteConfig(hostname) {
  for (const [domain, config] of Object.entries(SITE_CONFIGS)) {
    if (domain !== "default" && hostname.includes(domain)) {
      return { site: domain, config };
    }
  }
  return { site: "unknown", config: SITE_CONFIGS["default"] };
}
