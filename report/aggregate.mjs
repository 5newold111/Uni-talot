// うにの占いの館 — 週次レポート集計スクリプト
// Netlify Forms (uni-hyoka) の直近7日間の送信を集計し、10項目のレポートを生成する。
// 実行環境: GitHub Actions (Node 20+) / 必要な環境変数: NETLIFY_AUTH_TOKEN
import { writeFileSync } from "node:fs";

const TOKEN = process.env.NETLIFY_AUTH_TOKEN;
if (!TOKEN) { console.error("NETLIFY_AUTH_TOKEN がありません"); process.exit(1); }
const H = { Authorization: `Bearer ${TOKEN}` };
const API = "https://api.netlify.com/api/v1";

const now = new Date();
const weekAgo = new Date(now.getTime() - 7 * 24 * 3600 * 1000);
const twoWeeksAgo = new Date(now.getTime() - 14 * 24 * 3600 * 1000);

// ---- データ取得 ----
async function json(url) {
  const r = await fetch(url, { headers: H });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return r.json();
}
const forms = await json(`${API}/forms`);
const form = forms.find(f => f.name === "uni-hyoka");
if (!form) {
  writeFileSync("report.md", buildEmpty("フォーム uni-hyoka がまだ登録されていません。サイトのデプロイとフォーム検出の有効化を確認してください。"));
  process.exit(0);
}
let subs = [];
for (let page = 1; page <= 10; page++) {
  const batch = await json(`${API}/forms/${form.id}/submissions?per_page=100&page=${page}`);
  subs = subs.concat(batch);
  if (batch.length < 100) break;
}
const rows = subs.map(s => ({ at: new Date(s.created_at), d: s.data || {} }));
const week = rows.filter(r => r.at >= weekAgo);
const prevWeek = rows.filter(r => r.at >= twoWeeksAgo && r.at < weekAgo);

if (week.length === 0) {
  writeFileSync("report.md", buildEmpty("この7日間の評価送信はありませんでした。"));
  process.exit(0);
}

// ---- 集計ヘルパ ----
const num = v => Number(v) || 0;
function groupBy(arr, key) {
  const m = new Map();
  for (const r of arr) {
    const k = (r.d[key] || "不明");
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(r);
  }
  return m;
}
const avg = arr => arr.length ? arr.reduce((a, r) => a + num(r.d.rating), 0) / arr.length : 0;
const f2 = n => n.toFixed(2);
const pct = (n, d) => d ? Math.round(n / d * 100) + "%" : "-";
function rankAvg(map, minN = 1) {
  return [...map.entries()].filter(([, v]) => v.length >= minN)
    .map(([k, v]) => ({ k, n: v.length, avg: avg(v) }))
    .sort((a, b) => b.avg - a.avg);
}
const JST = d => new Date(d.getTime() + 9 * 3600 * 1000);
const fmtD = d => `${d.getUTCMonth() + 1}/${d.getUTCDate()}`;
// 個人情報らしき並びを軽くマスク
const mask = s => String(s || "").replace(/[0-9]{4,}/g, "****")
  .replace(/[\w.+-]+@[\w-]+\.[\w.]+/g, "***@***").slice(0, 80);

// ---- 10項目 ----
const byTheme = groupBy(week, "theme");
const byTopic = groupBy(week, "topic");
const bySpread = groupBy(week, "spread");
const ratingCounts = [1, 2, 3].map(v => week.filter(r => num(r.d.rating) === v).length);

const topTopics = [...byTopic.entries()].sort((a, b) => b[1].length - a[1].length);
const samples = topTopics.slice(0, 3).flatMap(([t, v]) =>
  v.filter(r => r.d.concern).slice(0, 2).map(r => `- （${t}）「${mask(r.d.concern)}」`));

const dowNames = ["日", "月", "火", "水", "木", "金", "土"];
const dow = new Array(7).fill(0), hours = new Array(24).fill(0);
for (const r of week) { const j = JST(r.at); dow[j.getUTCDay()]++; hours[j.getUTCHours()]++; }
const topDow = dow.map((n, i) => ({ n, i })).sort((a, b) => b.n - a.n).slice(0, 2);
const topHours = hours.map((n, i) => ({ n, i })).filter(x => x.n > 0).sort((a, b) => b.n - a.n).slice(0, 3);

const majUp = week.filter(r => num(r.d.upright) * 2 >= num(r.d.total));
const majRev = week.filter(r => num(r.d.upright) * 2 < num(r.d.total));

const themeRank = rankAvg(byTheme);
const topicRank = rankAvg(byTopic);
const spreadRank = rankAvg(bySpread);

const term = `${fmtD(JST(weekAgo))}〜${fmtD(JST(now))}`;
let md = `# うにの占いの館 週次レポート（${term}）\n\n`;
md += `## 1. 総鑑定数（評価送信数）\n${week.length}件（前週 ${prevWeek.length}件 / ${prevWeek.length ? (week.length >= prevWeek.length ? "+" : "") + (week.length - prevWeek.length) + "件" : "前週データなし"}）\n\n`;
md += `## 2. 相談ジャンル別の件数\n` + [...byTheme.entries()].sort((a, b) => b[1].length - a[1].length)
  .map(([k, v]) => `- ${k}: ${v.length}件（${pct(v.length, week.length)}）`).join("\n") + "\n\n";
md += `## 3. 相談トピック別ランキング\n` + topTopics
  .map(([k, v], i) => `${i + 1}. ${k}: ${v.length}件`).join("\n") + "\n\n";
md += `## 4. 相談文の代表例（マスク済み）\n` + (samples.length ? samples.join("\n") : "- 相談文の入力はありませんでした") + "\n\n";
md += `## 5. 評価の分布\n- 少し: ${ratingCounts[0]}件 / 普通: ${ratingCounts[1]}件 / たくさん: ${ratingCounts[2]}件\n- 平均スコア: ${f2(avg(week))}（3点満点）\n\n`;
md += `## 6. ジャンル別の平均評価\n` + themeRank.map(x => `- ${x.k}: ${f2(x.avg)}（${x.n}件）`).join("\n") + "\n\n";
md += `## 7. トピック別の平均評価（高い順）\n` + topicRank.map(x => `- ${x.k}: ${f2(x.avg)}（${x.n}件）`).join("\n") + "\n\n";
md += `## 8. スプレッド別の利用と評価\n` + spreadRank.map(x => `- ${x.k}: ${x.n}件 / 平均 ${f2(x.avg)}`).join("\n") + "\n\n";
md += `## 9. 曜日・時間帯の傾向（JST）\n- 多い曜日: ${topDow.map(x => `${dowNames[x.i]}曜(${x.n}件)`).join("、")}\n- 多い時間帯: ${topHours.map(x => `${x.i}時台(${x.n}件)`).join("、")}\n\n`;
md += `## 10. 札の正逆と満足度\n- 正位置が多い結果: 平均 ${f2(avg(majUp))}（${majUp.length}件）\n- 逆位置が多い結果: 平均 ${f2(avg(majRev))}（${majRev.length}件）\n`;
md += majRev.length && avg(majRev) < avg(majUp) - 0.3
  ? `- 所見: 逆位置中心の結果で満足度が下がっています。逆位置の鑑定文のフォロー（前向きな締め）強化を検討。\n\n`
  : `- 所見: 札の出方による満足度の大きな偏りは見られません。\n\n`;

// 所見
const best = topicRank[0], worst = topicRank[topicRank.length - 1];
md += `## 今週の所見と改善提案\n`;
md += `- 最も多かった相談は「${topTopics[0]?.[0]}」（${topTopics[0]?.[1].length}件）。\n`;
if (best && worst && best.k !== worst.k)
  md += `- 満足度が高いのは「${best.k}」(${f2(best.avg)})、低いのは「${worst.k}」(${f2(worst.avg)})。「${worst.k}」向けの鑑定文・アドバイスの見直しを推奨。\n`;
md += `- 平均スコア${f2(avg(week))}。${avg(week) >= 2.5 ? "全体として高い満足度を維持。" : "改善余地あり。低評価トピックの文言強化を。"}\n`;

writeFileSync("report.md", md);
console.log(md);

function buildEmpty(reason) {
  return `# うにの占いの館 週次レポート\n\n${reason}\n\n（データが集まり始めると、10項目の分析レポートが自動生成されます）\n`;
}
