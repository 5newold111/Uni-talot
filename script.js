// ===== 状態管理 =====
const state = {
  theme: null,    // 選択したテーマキー
  spread: null,   // 選択したスプレッドキー
  needed: 0,      // 引くべき枚数
  picks: []       // 引いたカード { card, reversed }
};

// ===== 星空を生成 =====
function createStars() {
  const container = document.getElementById("stars");
  const count = 80;
  for (let i = 0; i < count; i++) {
    const s = document.createElement("div");
    s.className = "star";
    const size = Math.random() * 2.5 + 1;
    s.style.width = s.style.height = size + "px";
    s.style.left = Math.random() * 100 + "%";
    s.style.top = Math.random() * 100 + "%";
    s.style.setProperty("--dur", (Math.random() * 3 + 2) + "s");
    s.style.animationDelay = Math.random() * 3 + "s";
    container.appendChild(s);
  }
}

// ===== 画面切り替え =====
function showStep(id) {
  document.querySelectorAll(".step").forEach(el => el.classList.add("hidden"));
  document.getElementById(id).classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ===== ① テーマ選択画面 =====
function renderThemes() {
  const grid = document.getElementById("theme-grid");
  grid.innerHTML = "";
  for (const [key, t] of Object.entries(THEMES)) {
    const el = document.createElement("div");
    el.className = "choice-card";
    el.innerHTML = `<span class="icon">${t.icon}</span><span class="label">${t.name}</span>`;
    el.addEventListener("click", () => {
      state.theme = key;
      renderSpreads();
      showStep("step-spread");
    });
    grid.appendChild(el);
  }
}

// ===== ② スプレッド選択画面 =====
function renderSpreads() {
  const grid = document.getElementById("spread-grid");
  grid.innerHTML = "";
  for (const [key, s] of Object.entries(SPREADS)) {
    const el = document.createElement("div");
    el.className = "choice-card";
    el.innerHTML = `<span class="label">${s.name}</span><span class="desc">${s.desc}</span>`;
    el.addEventListener("click", () => {
      state.spread = key;
      state.needed = s.count;
      state.picks = [];
      renderDeck();
      showStep("step-draw");
    });
    grid.appendChild(el);
  }
}

// ===== ③ カードを引く画面 =====
function renderDeck() {
  const area = document.getElementById("deck-area");
  area.innerHTML = "";
  const spread = SPREADS[state.spread];
  document.getElementById("draw-hint").textContent =
    `${spread.name}：あと ${state.needed} 枚 引いてください`;
  document.getElementById("btn-reveal").classList.add("hidden");

  // シャッフルした順番でデッキを並べる（位置はランダム化）
  const order = shuffle([...Array(TAROT_CARDS.length).keys()]);

  order.forEach(cardIndex => {
    const c = document.createElement("div");
    c.className = "deck-card";
    c.addEventListener("click", () => pickCard(c, cardIndex));
    area.appendChild(c);
  });
}

function pickCard(el, cardIndex) {
  if (el.classList.contains("picked")) return;
  if (state.picks.length >= state.needed) return;

  el.classList.add("picked");
  // 正位置か逆位置かをランダムに決定
  const reversed = Math.random() < 0.5;
  state.picks.push({ card: TAROT_CARDS[cardIndex], reversed });

  const remaining = state.needed - state.picks.length;
  const hint = document.getElementById("draw-hint");

  if (remaining > 0) {
    hint.textContent = `あと ${remaining} 枚 引いてください`;
  } else {
    hint.textContent = "すべてのカードが揃いました ✨";
    // 残りのカードを無効化
    document.querySelectorAll(".deck-card:not(.picked)")
      .forEach(d => d.classList.add("disabled"));
    document.getElementById("btn-reveal").classList.remove("hidden");
  }
}

// ===== ④ 結果表示画面 =====
function showResult() {
  const spread = SPREADS[state.spread];
  const theme = THEMES[state.theme];
  document.getElementById("result-title").textContent =
    `${theme.icon} ${theme.name} ・ ${spread.name} の結果`;

  const wrap = document.getElementById("result-cards");
  wrap.innerHTML = "";

  state.picks.forEach((pick, i) => {
    const { card, reversed } = pick;
    const meaning = reversed ? card.reversed[state.theme] : card.upright[state.theme];
    const el = document.createElement("div");
    el.className = "tarot-result" + (reversed ? " reversed" : "");
    el.style.animationDelay = (i * 0.25) + "s";
    el.innerHTML = `
      <span class="position">${spread.positions[i]}</span>
      <div class="face">${card.symbol}</div>
      <div class="card-name">${card.name}</div>
      <div class="card-name-en">${card.nameEn}</div>
      <div class="orientation ${reversed ? "rev" : "up"}">
        ${reversed ? "逆位置 (Reversed)" : "正位置 (Upright)"}
      </div>
      <div class="keywords">
        ${card.keywords.map(k => `<span class="kw">${k}</span>`).join("")}
      </div>
      <div class="meaning">${meaning}</div>
    `;
    wrap.appendChild(el);
  });

  // 総合メッセージ
  const summary = document.getElementById("result-summary");
  summary.innerHTML =
    `<div class="summary-label">🌙 占い師より</div>${buildSummary()}`;

  showStep("step-result");
}

// 引いたカードから総合メッセージを組み立てる
function buildSummary() {
  const upCount = state.picks.filter(p => !p.reversed).length;
  const total = state.picks.length;
  const theme = THEMES[state.theme].name;

  let tone;
  if (upCount === total) {
    tone = `すべて正位置という、とても良い流れが出ています。今の${theme}は追い風に恵まれています。自信を持って進んでください。`;
  } else if (upCount === 0) {
    tone = `逆位置が並びましたが、これは「立ち止まって見つめ直す時」というメッセージです。焦らず、心の声に耳を傾けることで道は開けます。`;
  } else {
    tone = `正位置と逆位置が混じり、変化と調整の時期を示しています。良い流れを活かしつつ、注意すべき点にも目を向けることで、${theme}はより良い方向へ進むでしょう。`;
  }

  const firstCard = state.picks[0].card.name;
  return `今回引かれた最初のカードは「${firstCard}」。${tone}<br><br>` +
    `カードはあくまで心を映す鏡です。最後に未来を選び取るのは、あなた自身の意志であることを忘れないでください。`;
}

// ===== ユーティリティ =====
function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function restart() {
  state.theme = null;
  state.spread = null;
  state.picks = [];
  state.needed = 0;
  renderThemes();
  showStep("step-theme");
}

// ===== イベント登録 =====
document.getElementById("btn-reveal").addEventListener("click", showResult);
document.getElementById("btn-restart").addEventListener("click", restart);
document.querySelectorAll(".btn-back").forEach(btn => {
  btn.addEventListener("click", () => showStep("step-" + btn.dataset.back));
});

// ===== 初期化 =====
createStars();
renderThemes();
