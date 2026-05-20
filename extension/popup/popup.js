const API_BASE = "http://localhost:3000/api";
const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

// ===== タブ切替 =====
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`[data-tab-panel="${tab.dataset.tab}"]`).classList.add("active");
    if (tab.dataset.tab === "history") loadHistory();
  });
});

// ===== 共通: API key & エラーガイダンス =====
let API_KEY = "";
let ERROR_GUIDANCE = {};

chrome.storage.local.get(["apiKey"], result => {
  API_KEY = result.apiKey || "";
});

function authHeaders() {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

async function apiFetch(path, options = {}) {
  return fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { ...(options.headers || {}), ...authHeaders() },
  });
}

async function loadErrorGuidance() {
  if (Object.keys(ERROR_GUIDANCE).length) return ERROR_GUIDANCE;
  try {
    const lang = (navigator.language || "ja").split("-")[0];
    const r = await apiFetch("/errors/guidance", {
      headers: { "Accept-Language": lang },
    });
    if (r.ok) ERROR_GUIDANCE = (await r.json()).guidance || {};
  } catch (_) {}
  return ERROR_GUIDANCE;
}

// ===== 単発タブ =====
const btn = document.getElementById("startBtn");
const statusDiv = document.getElementById("status");
const productDiv = document.getElementById("productInfo");
const guidanceDiv = document.getElementById("guidance");
const progressEl = document.getElementById("progress");
const progressBar = document.getElementById("progressBar");
const previewWrap = document.getElementById("previewWrap");
const modelViewer = document.getElementById("modelViewer");

function setStatus(message, type = "") {
  statusDiv.textContent = message;
  statusDiv.className = type;
}
function setProgress(stepIndex, totalSteps, state = "") {
  if (totalSteps > 0) {
    progressEl.classList.add("visible");
    const pct = Math.max(0, Math.min(100, (stepIndex / totalSteps) * 100));
    progressBar.style.width = `${pct}%`;
  }
  progressEl.classList.remove("success", "error");
  if (state) progressEl.classList.add(state);
}
function hideProgress() {
  progressEl.classList.remove("visible", "success", "error");
  progressBar.style.width = "0%";
}
function showGuidance(code) {
  if (!code || !ERROR_GUIDANCE[code]) { guidanceDiv.style.display = "none"; return; }
  guidanceDiv.textContent = `💡 ${ERROR_GUIDANCE[code]}`;
  guidanceDiv.style.display = "block";
}
function showPreview(glbFilename) {
  if (!glbFilename) return;
  // バックエンドの /output/<name> 静的配信から取得
  previewWrap.style.display = "block";
  const url = `http://localhost:3000/output/${encodeURIComponent(glbFilename)}`;
  modelViewer.setAttribute("src", url);
}

async function getProductDataFromActiveTab(tabId) {
  try {
    const response = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PRODUCT" });
    if (response && response.success && response.data) return response.data;
  } catch (_) {}
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["scrapers/site_configs.js", "content_scripts/scraper.js"],
  });
  const response = await chrome.tabs.sendMessage(tabId, { type: "EXTRACT_PRODUCT" });
  if (!response || !response.success) {
    throw new Error(response?.error || "商品情報の取得に失敗しました");
  }
  return response.data;
}

async function pollJob(jobId, onProgress) {
  const start = Date.now();
  while (Date.now() - start < POLL_TIMEOUT_MS) {
    const res = await apiFetch(`/status/${jobId}`);
    if (!res.ok) throw new Error(`ステータス取得失敗: ${res.status}`);
    const job = await res.json();
    if (onProgress) onProgress(job);
    if (job.status === "success") return job;
    if (job.status === "error") {
      const err = new Error(job.error || job.message || "サーバーエラー");
      err.code = job.error_code;
      throw err;
    }
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
  }
  throw new Error("タイムアウトしました");
}

btn.addEventListener("click", async () => {
  btn.disabled = true;
  setStatus("[準備中] 商品ページの情報を取得しています...");
  productDiv.style.display = "none";
  previewWrap.style.display = "none";
  guidanceDiv.style.display = "none";
  hideProgress();
  await loadErrorGuidance();

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const productData = await getProductDataFromActiveTab(tab.id);
    if (!productData.product_name) {
      throw new Error("商品名が取得できませんでした");
    }

    productDiv.style.display = "block";
    productDiv.innerHTML = `
      <strong>${productData.product_name}</strong><br>
      W${productData.dimensions.width_cm}×D${productData.dimensions.depth_cm}×H${productData.dimensions.height_cm}cm<br>
      画像: ${productData.images.length}枚
    `;

    setStatus("バックエンドにジョブを送信しています...");
    const response = await apiFetch("/process", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `サーバーエラー: ${response.status}`);
    }
    const { job_id } = await response.json();
    setStatus(`ジョブ受付 (${job_id})。処理状況を取得中...`);

    const job = await pollJob(job_id, j => {
      setStatus(j.message || `状態: ${j.status}`);
      setProgress(j.step_index, j.total_steps);
    });
    setProgress(job.total_steps, job.total_steps, "success");
    const glbName = job.result?.glb?.split("/").pop() || "";
    setStatus(`✅ 完了！\n「${job.result?.product || productData.product_name}」をHomestylerに登録しました`, "success");
    showPreview(glbName);

  } catch (error) {
    setProgress(0, 1, "error");
    setStatus(`エラー: ${error.message}`, "error");
    if (error.code) showGuidance(error.code);
    console.error("EC3D-Bridge エラー:", error);
  } finally {
    btn.disabled = false;
  }
});

// ===== 一括投入タブ =====
const bulkBtn = document.getElementById("bulkStartBtn");
const bulkStatusDiv = document.getElementById("bulkStatus");
const bulkUrlsTA = document.getElementById("bulkUrls");

function setBulkStatus(msg, type = "") {
  bulkStatusDiv.textContent = msg;
  bulkStatusDiv.className = type;
}

async function waitForTabComplete(tabId) {
  return new Promise(resolve => {
    const listener = (updatedId, info) => {
      if (updatedId === tabId && info.status === "complete") {
        chrome.tabs.onUpdated.removeListener(listener);
        resolve();
      }
    };
    chrome.tabs.onUpdated.addListener(listener);
  });
}

bulkBtn.addEventListener("click", async () => {
  const urls = bulkUrlsTA.value.split("\n").map(s => s.trim()).filter(s => s.startsWith("http"));
  if (urls.length === 0) {
    setBulkStatus("有効なURLが見つかりません", "error");
    return;
  }
  bulkBtn.disabled = true;
  let success = 0, failed = 0;
  for (let i = 0; i < urls.length; i++) {
    const url = urls[i];
    setBulkStatus(`[${i + 1}/${urls.length}] ${url.slice(0, 50)}... を処理中`);
    try {
      const tab = await chrome.tabs.create({ url, active: false });
      await waitForTabComplete(tab.id);
      const data = await getProductDataFromActiveTab(tab.id);
      await chrome.tabs.remove(tab.id);
      if (!data.product_name) throw new Error("商品データ取得失敗");

      const r = await apiFetch("/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      success++;
    } catch (e) {
      failed++;
      console.error(`一括投入失敗: ${url}`, e);
    }
  }
  setBulkStatus(`完了: 成功 ${success} / 失敗 ${failed} (合計 ${urls.length})`,
                failed === 0 ? "success" : "error");
  bulkBtn.disabled = false;
});

// ===== 履歴タブ =====
const historyList = document.getElementById("historyList");
document.getElementById("refreshHistoryBtn").addEventListener("click", loadHistory);

function timeAgo(ts) {
  const diff = (Date.now() / 1000) - ts;
  if (diff < 60) return `${Math.floor(diff)}秒前`;
  if (diff < 3600) return `${Math.floor(diff / 60)}分前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}時間前`;
  return `${Math.floor(diff / 86400)}日前`;
}

async function loadHistory() {
  historyList.innerHTML = '<li class="small-muted">読み込み中...</li>';
  try {
    const r = await apiFetch("/jobs?limit=50");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const { jobs } = await r.json();
    if (jobs.length === 0) {
      historyList.innerHTML = '<li class="small-muted">まだジョブがありません</li>';
      return;
    }
    historyList.innerHTML = jobs.map(j => {
      const canCancel = j.status === "queued" || j.status === "running";
      return `
      <li class="history-item" data-job-id="${j.id}">
        <span class="badge ${j.status}">${j.status}</span>
        <span class="name">${escapeHtml(j.product_name)}</span>
        <div class="meta">
          ${timeAgo(j.created_at)} · ステップ ${j.step_index}/${j.total_steps}
          ${j.error_code ? `· <code>${j.error_code}</code>` : ""}
          ${canCancel ? `· <button class="link cancel-btn" data-job-id="${j.id}">キャンセル</button>` : ""}
        </div>
      </li>`;
    }).join("");
    historyList.querySelectorAll(".cancel-btn").forEach(btn => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const jid = btn.dataset.jobId;
        btn.disabled = true;
        try {
          await apiFetch(`/jobs/${jid}/cancel`, { method: "POST" });
          loadHistory();
        } catch (err) {
          alert(`キャンセル失敗: ${err.message}`);
          btn.disabled = false;
        }
      });
    });
  } catch (e) {
    historyList.innerHTML = `<li class="small-muted error">読み込み失敗: ${e.message}</li>`;
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}
