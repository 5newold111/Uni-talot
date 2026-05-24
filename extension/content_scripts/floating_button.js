/**
 * EC サイトの商品ページに「3D化」フローティングボタンを注入する。
 *
 * 設計:
 *   - 対応 EC サイト (manifest.json の matches) でのみ読み込まれる
 *   - 右下に固定表示、ページ DOM を一切汚さない (Shadow DOM 利用)
 *   - 1 クリックで extractProductData() → /api/process → 状態ポーリング
 *   - 状態をボタン上で可視化 (idle/loading/success/error)
 *   - ユーザーが「×」で当該ページのみ非表示にできる (chrome.storage 永続化)
 *   - グローバル無効化は popup の設定で行う想定 (ec3d_fab_disabled キー)
 *
 * 依存: 同じく content_scripts に登録されている scraper.js (extractProductData)
 *      と site_configs.js が先に読み込まれていること。
 */
(() => {
  const FAB_ID = "ec3d-bridge-fab-root";
  const API_BASE = "http://localhost:3000/api";
  const POLL_INTERVAL_MS = 2000;
  const POLL_TIMEOUT_MS = 5 * 60 * 1000;

  // 既に注入済みなら何もしない (二重注入防止)
  if (document.getElementById(FAB_ID)) return;

  // ユーザーがグローバル / このページで無効化していないか確認
  function shouldRender(cb) {
    if (!window.chrome?.storage?.local) {
      cb(true);
      return;
    }
    const pageKey = `ec3d_fab_dismissed:${location.hostname}${location.pathname}`;
    chrome.storage.local.get(["ec3d_fab_disabled", pageKey], (result) => {
      if (result.ec3d_fab_disabled) return cb(false);
      if (result[pageKey]) return cb(false);
      cb(true);
    });
  }

  // 商品ページっぽいか軽く判定 (h1 と img が複数あれば商品ページとみなす)
  // 商品検索結果やトップページには出さない
  function looksLikeProductPage() {
    const hasH1 = document.querySelectorAll("h1, [class*='item_name'], [class*='product-name'], [data-testid='product-title']").length > 0;
    const hasManyImages = document.querySelectorAll("img").length >= 3;
    return hasH1 && hasManyImages;
  }

  function buildButton() {
    // Host element: page DOM に 1 つだけ追加し、内部は Shadow DOM
    // (ページ側 CSS の影響を受けず、こちらの CSS もページに漏らさない)
    const host = document.createElement("div");
    host.id = FAB_ID;
    host.style.cssText = "all:initial; position:fixed; bottom:24px; right:24px; z-index:2147483647;";
    const shadow = host.attachShadow({ mode: "open" });

    const style = document.createElement("style");
    style.textContent = `
      .fab {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans", sans-serif;
        display: flex; align-items: center; gap: 8px;
        background: #2c5364; color: white;
        padding: 12px 16px; border-radius: 28px;
        box-shadow: 0 6px 16px rgba(0,0,0,0.18), 0 0 0 1px rgba(255,255,255,0.06);
        cursor: pointer; user-select: none;
        font-size: 13px; font-weight: 600;
        transition: transform 0.15s ease, background 0.2s ease;
      }
      .fab:hover { transform: translateY(-2px); }
      .fab.loading { background: #3d6878; cursor: progress; }
      .fab.success { background: #1d6e35; }
      .fab.error   { background: #8b2424; cursor: pointer; }
      .fab.disabled { opacity: 0.6; cursor: not-allowed; }
      .icon { font-size: 16px; line-height: 1; }
      .dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: #7eb6c4;
      }
      .fab.loading .dot { animation: pulse 1.2s infinite ease-in-out; }
      @keyframes pulse {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.4); }
      }
      .close {
        margin-left: 4px; padding: 2px 6px; border-radius: 50%;
        font-size: 14px; line-height: 1; opacity: 0.7; cursor: pointer;
      }
      .close:hover { opacity: 1; background: rgba(255,255,255,0.15); }
      .progress {
        margin-top: 6px; height: 3px; width: 100%;
        background: rgba(255,255,255,0.2); border-radius: 2px; overflow: hidden;
      }
      .progress > .bar {
        height: 100%; width: 0%; background: rgba(255,255,255,0.85);
        transition: width 0.35s ease-out;
      }
      .container { display: flex; flex-direction: column; align-items: stretch; gap: 4px; }
    `;
    shadow.appendChild(style);

    const container = document.createElement("div");
    container.className = "container";

    const fab = document.createElement("div");
    fab.className = "fab";
    fab.setAttribute("role", "button");
    fab.setAttribute("aria-label", "この商品を 3D 化");
    fab.innerHTML = `
      <span class="icon">🪑</span>
      <span class="label">3D化する</span>
      <span class="dot"></span>
      <span class="close" title="このページでは非表示にする">×</span>
    `;
    container.appendChild(fab);

    const progressEl = document.createElement("div");
    progressEl.className = "progress";
    progressEl.style.display = "none";
    progressEl.innerHTML = '<div class="bar"></div>';
    container.appendChild(progressEl);

    shadow.appendChild(container);
    document.documentElement.appendChild(host);

    return { host, shadow, fab, progressEl, container };
  }

  // ===== state machine =====
  function setState(fab, state, label) {
    fab.classList.remove("loading", "success", "error", "disabled");
    if (state) fab.classList.add(state);
    const labelEl = fab.querySelector(".label");
    if (label && labelEl) labelEl.textContent = label;
  }

  function setProgress(progressEl, idx, total) {
    if (total <= 0) {
      progressEl.style.display = "none";
      return;
    }
    progressEl.style.display = "block";
    const bar = progressEl.querySelector(".bar");
    bar.style.width = `${Math.min(100, (idx / total) * 100)}%`;
  }

  async function postToBackend(productData) {
    const res = await fetch(`${API_BASE}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async function pollJob(jobId, onUpdate) {
    const start = Date.now();
    while (Date.now() - start < POLL_TIMEOUT_MS) {
      const r = await fetch(`${API_BASE}/status/${jobId}`);
      if (!r.ok) throw new Error(`status ${r.status}`);
      const job = await r.json();
      if (onUpdate) onUpdate(job);
      if (job.status === "success") return job;
      if (job.status === "error") {
        const e = new Error(job.error || "サーバーエラー");
        e.code = job.error_code;
        throw e;
      }
      if (job.status === "cancelled") throw new Error("キャンセルされました");
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
    throw new Error("タイムアウトしました");
  }

  function attachHandlers({ host, fab, progressEl }) {
    // 「×」で当該ページのみ非表示 (chrome.storage に永続化)
    fab.querySelector(".close").addEventListener("click", (e) => {
      e.stopPropagation();
      const pageKey = `ec3d_fab_dismissed:${location.hostname}${location.pathname}`;
      if (window.chrome?.storage?.local) {
        chrome.storage.local.set({ [pageKey]: true });
      }
      host.remove();
    });

    let busy = false;
    fab.addEventListener("click", async () => {
      if (busy) return;
      // 失敗状態だったら再試行できるよう一旦リセット
      if (fab.classList.contains("error")) {
        setState(fab, "", "3D化する");
      }
      // extractProductData が同じ content_scripts でロード済みのはず
      if (typeof window.extractProductData !== "function") {
        // scraper.js が未ロード (順序問題)
        setState(fab, "error", "スクレーパー未ロード");
        return;
      }

      busy = true;
      setState(fab, "loading", "[1/3] 抽出中...");
      setProgress(progressEl, 0, 0);
      try {
        const data = window.extractProductData();
        if (!data.product_name) throw new Error("商品名が取得できません");
        setState(fab, "loading", "送信中...");
        const { job_id } = await postToBackend(data);
        const job = await pollJob(job_id, (j) => {
          setState(fab, "loading", j.message?.slice(0, 30) || j.step);
          setProgress(progressEl, j.step_index, j.total_steps);
        });
        setState(fab, "success", `✓ 完了 (${(job.result?.glb || "").split("/").pop()})`);
        setProgress(progressEl, job.total_steps, job.total_steps);
      } catch (e) {
        setState(fab, "error", `✗ ${e.message?.slice(0, 30) || "失敗"} (再試行)`);
        console.error("[ec3d-bridge fab]", e);
      } finally {
        busy = false;
      }
    });
  }

  // ===== entry =====
  function init() {
    if (!looksLikeProductPage()) return;
    shouldRender((render) => {
      if (!render) return;
      const refs = buildButton();
      attachHandlers(refs);
    });
  }

  // DOM が読まれてから注入 (CSR/SPA の遅延描画対応で念のため少し待つ)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
