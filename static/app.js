const HISTORY_KEY = "job_scam_history";
let lastCompanyUrls = null;
let lastCompanyName = "";

async function initAiProvider() {
  const sel = document.getElementById("aiProvider");
  const wrap = document.getElementById("aiProviderWrap");
  try {
    const res = await fetch("/api/ai/status");
    const st = await res.json();
    const p = st.provider || "none";
    if (p === "deepseek" && st.deepseek?.configured) sel.value = "deepseek";
    else if (p === "gemini" && st.gemini?.configured) sel.value = "gemini";
    else if (st.deepseek?.configured) sel.value = "deepseek";
    else if (st.gemini?.configured) sel.value = "gemini";
    else sel.value = "none";
    const tips = [];
    if (st.deepseek?.configured) tips.push(`DS:${st.deepseek.model}`);
    if (st.gemini?.configured) tips.push(`G:${st.gemini.model}`);
    wrap.title = tips.length ? tips.join(" · ") : st.setup?.deepseek || "";
  } catch (_) {
    sel.value = "none";
  }
}

initAiProvider();

const SAMPLE = `【居家客服 日结300 有手机就能做】先加微信详聊，岗前测评。
需垫付任务返利，招兼职人事代发职位，自备两部手机。`;

document.getElementById("btnSample").onclick = () => {
  document.getElementById("inputText").value = SAMPLE;
};
document.getElementById("btnClear").onclick = () => {
  document.getElementById("inputText").value = "";
  hideResult();
  hideCompanyLinks();
};
document.getElementById("btnAnalyze").onclick = runAnalyze;
document.getElementById("btnUrl").onclick = runUrlCheck;
document.getElementById("btnNote").onclick = saveNote;
document.getElementById("btnOpenBoth").onclick = openBothPlatforms;

renderHistory();

async function runAnalyze() {
  const text = document.getElementById("inputText").value.trim();
  if (!text) return;

  const btn = document.getElementById("btnAnalyze");
  btn.disabled = true;
  const provider = document.getElementById("aiProvider").value;
  const useAi = provider !== "none";
  btn.textContent = useAi ? "AI 分析中…" : "检测中…";
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        content_type: "auto",
        use_ai: useAi,
        provider: useAi ? provider : "none",
      }),
    });
    const data = await res.json();
    renderResult(data, text);
    await fillCompanyLinks(text);
    await renderHistoryFromServer();
  } catch (e) {
    alert("检测失败");
  } finally {
    btn.disabled = false;
    btn.textContent = "检测";
  }
}

async function fillCompanyLinks(text) {
  const res = await fetch("/api/company/from-text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, content_type: "auto" }),
  });
  const data = await res.json();
  if (!data.ok || !data.candidates?.length) {
    hideCompanyLinks();
    return;
  }
  const name = data.primary || data.candidates[0];
  document.getElementById("companyInput").value = name;
  lastCompanyUrls = data.urls;
  lastCompanyName = name;
  showCompanyLinks(name, data.urls, data.candidates.length);
}

function openBothPlatforms() {
  const name =
    document.getElementById("companyInput").value.trim() || lastCompanyName;
  if (!name || !lastCompanyUrls) {
    alert("未识别到公司名");
    return;
  }
  window.open(lastCompanyUrls.tianyancha, "_blank", "noopener");
  window.open(lastCompanyUrls.qcc, "_blank", "noopener");
}

function showCompanyLinks(name, urls, total) {
  const box = document.getElementById("companyLinks");
  const extra = total > 1 ? ` 等${total}家` : "";
  document.getElementById("companyDetectLabel").textContent =
    `识别到公司：${name}${extra} — 双开或单独跳转查实缴/参保`;
  document.getElementById("linkTyc").href = urls.tianyancha;
  document.getElementById("linkQcc").href = urls.qcc;
  document.getElementById("linkAqc").href = urls.aiqicha;
  box.classList.remove("hidden");
}

function hideCompanyLinks() {
  document.getElementById("companyLinks").classList.add("hidden");
  lastCompanyUrls = null;
  lastCompanyName = "";
}

async function runUrlCheck() {
  const url = document.getElementById("urlInput").value.trim();
  if (!url) return;
  const res = await fetch("/api/analyze/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  const data = await res.json();
  renderResult(
    {
      risk_score: data.risk_score,
      risk_level: data.risk_level,
      headline: data.warning ? "链接存在仿冒风险" : "链接未命中明显仿冒特征",
      actions: data.safe
        ? ["仍建议在官网核实后再访问", "勿在可疑页面填写个人信息"]
        : ["不要打开或填写个人信息", "通过官方渠道核实链接"],
      matches: data.warning
        ? [{ category_name: "链接", weight: 0, hits: [data.warning] }]
        : [],
      suggestions: data.safe
        ? ["未命中仿冒特征，仍建议在官网核实。"]
        : ["不要打开或填写个人信息。"],
      highlight_terms: [],
      url_warnings: data.warning ? [`${url} — ${data.warning}`] : [],
    },
    url
  );
}

function renderResult(data, sourceText) {
  document.getElementById("emptyState").classList.add("hidden");
  document.getElementById("resultContent").classList.remove("hidden");

  const typeEl = document.getElementById("contentTypeLabel");
  if (typeEl) typeEl.textContent = data.content_type_label || "自动识别";

  document.getElementById("headlineText").textContent = data.headline || "";
  document.getElementById("actionList").innerHTML = (data.actions || [])
    .map((a) => `<li>${escapeHtml(a)}</li>`)
    .join("");

  const levelEl = document.getElementById("riskLevel");
  const card = document.getElementById("scoreCard");
  const display = data.risk_level_display || data.risk_level;
  card.className = "score-card";
  levelEl.className = "badge";
  if (data.risk_level === "高危") {
    card.classList.add("level-high");
    levelEl.classList.add("high");
  } else if (data.risk_level === "中危") {
    card.classList.add("level-mid");
    levelEl.classList.add("mid");
  } else {
    card.classList.add("level-low");
    levelEl.classList.add("low");
  }
  levelEl.textContent = display;
  const scoreHint = document.getElementById("scoreHint");
  if (scoreHint) {
    const aiName =
      data.ai?.provider === "deepseek"
        ? "DeepSeek"
        : data.ai?.provider === "gemini"
          ? "Gemini"
          : "AI";
    if (data.ai?.ok) {
      scoreHint.textContent = `含 ${aiName} 补充`;
    } else if ((data.biz_warnings || []).length) {
      scoreHint.textContent = "含工商信号";
    } else {
      scoreHint.textContent = "话术+工商综合";
    }
  }

  const bizBox = document.getElementById("bizWarnings");
  if (data.biz_warnings?.length) {
    bizBox.classList.remove("hidden");
    bizBox.innerHTML =
      "<h3>工商/经营信号</h3><ul>" +
      data.biz_warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("") +
      "</ul>";
  } else {
    bizBox.classList.add("hidden");
    bizBox.innerHTML = "";
  }

  const aiBlock = document.getElementById("aiBlock");
  const aiTitle = document.querySelector("#aiBlock h3");
  if (aiTitle) aiTitle.textContent = `${aiName} 研判`;
  if (data.ai?.ok && (data.ai.summary || data.ai.red_flags?.length)) {
    aiBlock.classList.remove("hidden");
    document.getElementById("aiSummary").textContent = data.ai.summary || "";
    document.getElementById("aiRedFlags").innerHTML = [
      ...(data.ai.scam_types || []).map((t) => `<li><b>类型</b> ${escapeHtml(t)}</li>`),
      ...(data.ai.red_flags || []).map((f) => `<li>${escapeHtml(f)}</li>`),
    ].join("");
  } else if (data.ai?.used && data.ai?.error) {
    aiBlock.classList.remove("hidden");
    document.getElementById("aiSummary").textContent = `${aiName} 未成功：${data.ai.error}`;
    document.getElementById("aiRedFlags").innerHTML = "";
  } else if (data.ai?.used && data.ai?.skipped && data.ai?.skip_reason) {
    aiBlock.classList.remove("hidden");
    document.getElementById("aiSummary").textContent = data.ai.skip_reason;
    document.getElementById("aiRedFlags").innerHTML = "";
  } else {
    aiBlock.classList.add("hidden");
  }

  const hBox = document.getElementById("highlightBox");
  const hText = document.getElementById("highlightText");
  if (data.highlight_terms?.length && sourceText) {
    hBox.classList.remove("hidden");
    hText.innerHTML = highlightSource(sourceText, data.highlight_terms);
  } else {
    hBox.classList.add("hidden");
  }

  const urlBox = document.getElementById("urlWarnings");
  if (data.url_warnings?.length) {
    urlBox.classList.remove("hidden");
    urlBox.innerHTML = data.url_warnings.map((w) => `<p>⚠ ${escapeHtml(w)}</p>`).join("");
  } else {
    urlBox.classList.add("hidden");
  }

  const matchList = document.getElementById("matchList");
  matchList.innerHTML = data.matches?.length
    ? data.matches
        .map(
          (m) =>
            `<li><b>${escapeHtml(m.category_name)}</b><br>${m.hits.map(escapeHtml).join("<br>")}</li>`
        )
        .join("")
    : "<li>未命中规则</li>";

  document.getElementById("suggestionList").innerHTML = (data.suggestions || [])
    .map((s) => `<li>${escapeHtml(s)}</li>`)
    .join("");

  document.getElementById("companyBlock").classList.add("hidden");
}

function highlightSource(text, terms) {
  let html = escapeHtml(text);
  const sorted = [...terms].sort((a, b) => b.length - a.length);
  for (const term of sorted) {
    if (!term) continue;
    const re = new RegExp(escapeRegExp(term), "gi");
    html = html.replace(re, (m) => `<mark>${escapeHtml(m)}</mark>`);
  }
  return html;
}

function hideResult() {
  document.getElementById("emptyState").classList.remove("hidden");
  document.getElementById("resultContent").classList.add("hidden");
}

async function saveNote() {
  const text = document.getElementById("inputText").value.trim();
  if (!text) return;
  const res = await fetch("/api/note", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text,
      note: document.getElementById("noteInput")?.value?.trim() || null,
    }),
  });
  const data = await res.json();
  const el = document.getElementById("noteMsg");
  if (el) {
    el.textContent = data.ok
      ? `已记入本地 (${data.risk_level} ${data.risk_score}分)`
      : "保存失败";
  }
}

async function renderHistoryFromServer() {
  try {
    const res = await fetch("/api/history?limit=8");
    const data = await res.json();
    renderHistoryBar(data.items || []);
  } catch (_) {
    renderHistoryBar([]);
  }
}

function renderHistoryBar(list) {
  const bar = document.getElementById("historyBar");
  if (!list.length) {
    bar.classList.add("hidden");
    return;
  }
  bar.classList.remove("hidden");
  bar.innerHTML =
    '<span class="hist-label">最近：</span>' +
    list
      .map(
        (h, i) =>
          `<button type="button" class="hist-btn" data-i="${i}">${escapeHtml(h.risk_level || "?")} ${h.risk_score ?? "—"}</button>`
      )
      .join("");

  bar.querySelectorAll(".hist-btn").forEach((btn) => {
    btn.onclick = () => {
      const h = list[Number(btn.dataset.i)];
      document.getElementById("inputText").value = h.text || h.preview || "";
      runAnalyze();
    };
  });
}

async function renderHistory() {
  await renderHistoryFromServer();
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const ta = document.getElementById("inputText");
    if (ta.value.trim()) {
      ta.value = "";
      hideResult();
      hideCompanyLinks();
    }
  }
});
