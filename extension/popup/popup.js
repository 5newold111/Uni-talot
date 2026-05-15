const API_BASE = "http://localhost:3000/api";
const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;  // 5分でポーリング打ち切り

const btn = document.getElementById("startBtn");
const statusDiv = document.getElementById("status");
const productDiv = document.getElementById("productInfo");

function setStatus(message, type = "") {
  statusDiv.textContent = message;
  statusDiv.className = type;
}

async function getProductData(tabId) {
  try {
    const response = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PRODUCT" });
    if (response && response.success && response.data) {
      return response.data;
    }
  } catch (e) {
    // content_script未注入の場合は次でinjectする
  }

  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["scrapers/site_configs.js", "content_scripts/scraper.js"]
  });

  const response = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PRODUCT" });
  if (!response || !response.success) {
    throw new Error(response?.error || "商品情報の取得に失敗しました");
  }
  return response.data;
}

async function pollJob(jobId) {
  const start = Date.now();
  while (Date.now() - start < POLL_TIMEOUT_MS) {
    const res = await fetch(`${API_BASE}/status/${jobId}`);
    if (!res.ok) {
      throw new Error(`ステータス取得失敗: ${res.status}`);
    }
    const job = await res.json();
    setStatus(job.message || `状態: ${job.status}`);

    if (job.status === "success") {
      return job;
    }
    if (job.status === "error") {
      throw new Error(job.error || job.message || "サーバーでエラーが発生しました");
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error("タイムアウトしました");
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  setStatus("[準備中] 商品ページの情報を取得しています...");
  productDiv.style.display = "none";

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const productData = await getProductData(tab.id);

    if (!productData.product_name) {
      throw new Error("商品名が取得できませんでした。対応ECサイトのページか確認してください");
    }

    productDiv.style.display = "block";
    productDiv.innerHTML = `
      <strong>${productData.product_name}</strong><br>
      W${productData.dimensions.width_cm}×D${productData.dimensions.depth_cm}×H${productData.dimensions.height_cm}cm<br>
      画像: ${productData.images.length}枚
    `;

    setStatus("バックエンドにジョブを送信しています...");

    const response = await fetch(`${API_BASE}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData)
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `サーバーエラー: ${response.status}`);
    }

    const { job_id } = await response.json();
    setStatus(`ジョブ受付 (${job_id})。処理状況を取得中...`);

    const job = await pollJob(job_id);
    const glb = job.result?.glb ? `\n生成GLB: ${job.result.glb.split('/').pop()}` : "";
    setStatus(`完了！\n「${job.result?.product || productData.product_name}」をHomestylerに登録しました${glb}`, "success");

  } catch (error) {
    setStatus(`エラー: ${error.message}`, "error");
    console.error("EC3D-Bridge エラー:", error);
  } finally {
    btn.disabled = false;
  }
});
