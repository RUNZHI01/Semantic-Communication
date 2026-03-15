const state = {
  snapshot: null,
  systemStatus: null,
  activeAct: "act1",
  selectedImageIndex: 0,
  currentResult: null,
  baselineResult: null,
  faultResult: null,
};

function docHref(path) {
  return `/docs?path=${encodeURIComponent(path)}`;
}

function fetchJSON(url, options = {}) {
  return fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  }).then(async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.message || `Request failed: ${response.status}`);
    }
    return payload;
  });
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function toneClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("online") || normalized.includes("live") || normalized.includes("pass") || normalized.includes("ready")) {
    return "tone-online";
  }
  if (normalized.includes("degraded") || normalized.includes("warning") || normalized.includes("fallback") || normalized.includes("replay")) {
    return "tone-degraded";
  }
  if (normalized.includes("offline") || normalized.includes("fail") || normalized.includes("deny") || normalized.includes("timeout")) {
    return "tone-offline";
  }
  return "tone-neutral";
}

function lampClass(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized.includes("online") || normalized.includes("ready") || normalized.includes("green")) {
    return "lamp-online";
  }
  if (normalized.includes("warning") || normalized.includes("degraded") || normalized.includes("yellow")) {
    return "lamp-warning";
  }
  if (normalized.includes("danger") || normalized.includes("red") || normalized.includes("fault") || normalized.includes("deny")) {
    return "lamp-danger";
  }
  return "";
}

function formatMaybeMs(value) {
  if (value === null || value === undefined || value === "") return "NA";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return String(value);
  return `${numeric.toFixed(numeric >= 100 ? 1 : 3).replace(/\.000$/, "").replace(/(\.\d)00$/, "$1")} ms`;
}

function fieldLabel(field) {
  const labels = {
    host: "主机",
    user: "用户名",
    password: "密码",
    port: "SSH 端口",
    env_file: "推理 env",
  };
  return labels[field] || field;
}

function summarizeMissing(fields) {
  if (!fields || !fields.length) return "无";
  return fields.map((field) => fieldLabel(field)).join("、");
}

function renderFieldChip(label, value, state) {
  const tone = state === "preloaded" ? "tone-online" : state === "missing" ? "tone-degraded" : "tone-neutral";
  return `
    <div class="field-chip ${tone}" data-state="${escapeHtml(state)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderLinks(links) {
  if (!links || !links.length) return "";
  return `
    <div class="inline-links">
      ${links
        .map((link) => `<a class="doc-link" href="${docHref(link.path)}">${escapeHtml(link.label)}</a>`)
        .join("")}
    </div>
  `;
}

function statCard(label, value, caption) {
  return `
    <div class="mini-metric">
      <div class="label">${escapeHtml(label)}</div>
      <div class="value">${escapeHtml(value)}</div>
      <div class="compact-copy">${escapeHtml(caption)}</div>
    </div>
  `;
}

function kpiCard(label, value, note, lamp = "") {
  return `
    <article class="status-kpi">
      <div class="label">${escapeHtml(label)}</div>
      <div class="inline-actions">
        <div class="status-dot ${lampClass(lamp)}"></div>
        <div class="value">${escapeHtml(value)}</div>
      </div>
      <div class="compact-copy">${escapeHtml(note)}</div>
    </article>
  `;
}

function setFeedback(message, tone) {
  const banner = document.getElementById("feedbackBanner");
  if (!message) {
    banner.hidden = true;
    banner.textContent = "";
    banner.removeAttribute("data-tone");
    return;
  }
  banner.hidden = false;
  banner.setAttribute("data-tone", tone);
  banner.textContent = message;
}

function renderTop(snapshot, systemStatus) {
  document.getElementById("heroSummary").textContent =
    `trusted current SHA ${snapshot.project.trusted_current_sha.slice(0, 12)} 已与当前演示材料对齐。` +
    ` 第一幕优先展示板卡状态，第二幕和第三幕分别对应重建与正式口径对比，第四幕保留 FIT-01 / FIT-02 / FIT-03 证据。`;

  const modePill = document.getElementById("modePill");
  modePill.className = `mode-pill ${toneClass(systemStatus.execution_mode.tone)}`;
  modePill.textContent = systemStatus.execution_mode.label;
  document.getElementById("modeSummary").textContent = systemStatus.execution_mode.summary;
  document.getElementById("generatedAt").textContent = `快照时间 ${snapshot.generated_at}`;
  document.getElementById("topStats").innerHTML = [
    statCard("P0 里程碑", String(snapshot.stats.p0_milestones_verified), "演示系统保留的板级证据项"),
    statCard("FIT 最终通过", String(snapshot.stats.fit_final_pass_count), "正式收口后的通过项"),
    statCard("Payload", `${snapshot.stats.payload_current_ms} ms`, "正式 current 口径"),
    statCard("端到端", `${snapshot.stats.end_to_end_current_ms} ms/image`, "正式 current 口径"),
  ].join("");
}

function renderBoardAccess(systemStatus) {
  const access = systemStatus.board_access;
  const defaults = access.preloaded_defaults || {};
  const currentMissing = access.missing_inference_fields_by_variant?.current || access.missing_inference_fields || [];
  const baselineMissing = access.missing_inference_fields_by_variant?.baseline || [];
  const onlyPasswordMissing =
    access.missing_connection_fields.length === 1 && access.missing_connection_fields[0] === "password";

  if (access.connection_ready) {
    document.getElementById("boardAccessSummary").textContent =
      `当前会话已可复用：${access.user || "未填用户"}@${access.host || "未填主机"}:${access.port}。`;
  } else if (defaults.active && onlyPasswordMissing) {
    document.getElementById("boardAccessSummary").textContent =
      `已预载 ${access.user || "未填用户"}@${access.host || "未填主机"}:${access.port} 与推理 env；当前只差密码。`;
  } else if (access.configured) {
    document.getElementById("boardAccessSummary").textContent =
      `已记录部分会话信息：${access.user || "未填用户"}@${access.host || "未填主机"}:${access.port}。`;
  } else {
    document.getElementById("boardAccessSummary").textContent = "尚未录入板卡会话。";
  }
  if (access.host) document.getElementById("hostInput").value = access.host;
  if (access.user) document.getElementById("userInput").value = access.user;
  if (access.port) document.getElementById("portInput").value = access.port;
  if (access.env_file) document.getElementById("envFileInput").value = access.env_file;
  document.getElementById("passwordInput").placeholder = access.has_password
    ? "已保存在当前 demo 进程内；留空则继续复用"
    : defaults.active
      ? "当前唯一必填项；输入一次后复用"
      : "仅保存在当前 demo 进程内";

  const sourceNotes = [];
  if (defaults.ssh_env_file) sourceNotes.push(`SSH 默认：${defaults.ssh_env_file}`);
  if (defaults.inference_env_file) sourceNotes.push(`推理默认：${defaults.inference_env_file}`);
  document.getElementById("boardAccessHints").innerHTML = `
    <div class="credential-chip-row">
      ${renderFieldChip(fieldLabel("host"), access.host || "未预载", access.field_sources?.host || "missing")}
      ${renderFieldChip(fieldLabel("user"), access.user || "未预载", access.field_sources?.user || "missing")}
      ${renderFieldChip(fieldLabel("port"), String(access.port || "未预载"), access.field_sources?.port || "missing")}
      ${renderFieldChip(fieldLabel("env_file"), access.env_file || "未预载", access.field_sources?.env_file || "missing")}
      ${renderFieldChip(fieldLabel("password"), access.has_password ? "已录入" : "待填写", access.field_sources?.password || "missing")}
    </div>
    <div class="credential-note">
      SSH 会话：${escapeHtml(access.connection_ready ? "已就绪" : `仍缺 ${summarizeMissing(access.missing_connection_fields)}`)}。
      Current：${escapeHtml(access.inference_ready_variants?.current ? "已就绪" : `仍缺 ${summarizeMissing(currentMissing)}`)}。
      Baseline：${escapeHtml(access.inference_ready_variants?.baseline ? "已就绪" : `仍缺 ${summarizeMissing(baselineMissing)}`)}。
    </div>
    ${sourceNotes.length ? `<div class="credential-note">${escapeHtml(sourceNotes.join(" ｜ "))}</div>` : ""}
  `;
}

function renderAct1(snapshot, systemStatus) {
  const live = systemStatus.live;
  document.getElementById("act1StatusNote").textContent = live.status_note;
  document.getElementById("act1StatusGrid").innerHTML = [
    kpiCard("飞腾派 / SSH", live.board_online ? "在线" : "未在线", live.board_online ? "当前演示进程已拿到最新只读读数。" : "尚无新的在线读数，回退到证据。", live.board_online ? "online" : "offline"),
    kpiCard("OpenAMP / remoteproc", live.remoteproc_state, `RPMsg 设备：${live.rpmsg_device}`, live.remoteproc_state),
    kpiCard("guard_state", live.guard_state, `last_fault_code：${live.last_fault_code}`, live.guard_state),
    kpiCard("运行目标", live.target, `runtime：${live.runtime}`, "online"),
  ].join("");

  const evidence = snapshot.board.evidence_status;
  document.getElementById("boardEvidenceCard").innerHTML = `
    <div class="status-pill tone-online">${escapeHtml(evidence.label)}</div>
    <div class="compact-copy">${escapeHtml(evidence.summary)}</div>
    <div class="status-meta">
      <span>remoteproc=${escapeHtml(evidence.transport.remoteproc_state)}</span>
      <span>RPMsg=${escapeHtml(evidence.transport.rpmsg_dev)}</span>
      <span>trusted SHA=${escapeHtml(evidence.trusted_current_sha.slice(0, 12))}</span>
    </div>
    ${renderLinks(evidence.evidence)}
  `;

  const current = snapshot.board.current_status;
  document.getElementById("boardLiveCard").innerHTML = `
    <div class="status-pill ${current.reachable ? "tone-online" : "tone-degraded"}">${escapeHtml(current.label)}</div>
    <div class="compact-copy">${escapeHtml(current.summary)}</div>
    <div class="status-meta">
      <span>读取时间=${escapeHtml(current.requested_at || "尚未执行")}</span>
      <span>guard=${escapeHtml(live.guard_state)}</span>
      <span>fault=${escapeHtml(live.last_fault_code)}</span>
    </div>
    ${renderLinks(current.evidence)}
  `;

  document.getElementById("milestonesGrid").innerHTML = snapshot.milestones
    .map(
      (item) => `
        <article class="milestone-card">
          <div class="milestone-meta">
            <span>${escapeHtml(item.stage)}</span>
            <span>${escapeHtml(item.mapped_id)}</span>
          </div>
          <h3>${escapeHtml(item.coverage_item)}</h3>
          <div class="status-pill ${toneClass(item.status)}">${escapeHtml(item.status)}</div>
          <div class="compact-copy">${escapeHtml(item.key_proof_point)}</div>
          ${renderLinks(item.evidence)}
        </article>
      `
    )
    .join("");
}

function renderSampleOptions(snapshot) {
  const select = document.getElementById("imageSelect");
  if (select.options.length) return;
  select.innerHTML = snapshot.guided_demo.sample_catalog
    .map(
      (item) =>
        `<option value="${item.index}">${escapeHtml(item.label)} | current PSNR ${Number(item.quality_preview.current_psnr_db || 0).toFixed(2)} dB</option>`
    )
    .join("");
  select.value = String(state.selectedImageIndex);
}

function barWidth(value, max) {
  if (!max || max <= 0) return 0;
  return Math.max(6, Math.round((value / max) * 100));
}

function renderInference(result) {
  if (!result) {
    document.getElementById("act2SourceLabel").textContent = "等待执行。";
    document.getElementById("timingBoard").innerHTML = "";
    document.getElementById("qualityMetrics").innerHTML = "";
    document.getElementById("inferenceMessage").textContent = "等待触发重建。";
    return;
  }
  document.getElementById("act2SourceLabel").textContent = `${result.source_label} | ${result.sample.label}`;
  document.getElementById("originalImage").src = result.original_image_b64;
  document.getElementById("reconstructedImage").src = result.reconstructed_image_b64;
  document.getElementById("inferenceMessage").textContent = result.message;

  const stageValues = result.timings.stages || [];
  const maxValue = Math.max(...stageValues.map((item) => Number(item.value_ms || 0)), 1);
  document.getElementById("timingBoard").innerHTML = stageValues
    .map((item) => {
      const emphasisClass = item.emphasis === "board" ? "bar-board" : item.emphasis === "total" ? "bar-total" : "bar-host";
      return `
        <div class="timing-row">
          <div class="timing-label">
            <span>${escapeHtml(item.label)}</span>
            <span>${formatMaybeMs(item.value_ms)}</span>
          </div>
          <div class="timing-bar"><span class="${emphasisClass}" style="width:${barWidth(Number(item.value_ms || 0), maxValue)}%"></span></div>
        </div>
      `;
    })
    .join("");

  document.getElementById("qualityMetrics").innerHTML = [
    `<div class="metric-chip">PSNR: ${Number(result.quality.psnr_db || 0).toFixed(2)} dB</div>`,
    `<div class="metric-chip">SSIM: ${Number(result.quality.ssim || 0).toFixed(4)}</div>`,
    `<div class="metric-chip">artifact: ${escapeHtml(String(result.artifact_sha).slice(0, 12))}</div>`,
  ].join("");
}

function comparisonCard(label, baselineMs, currentMs, improvementPct, speedupX, callout) {
  const maxValue = Math.max(baselineMs, currentMs, 1);
  return `
    <article class="comparison-card">
      <div class="comparison-title">${escapeHtml(label)}<span class="comparison-speedup">${speedupX.toFixed(1)}x / ${improvementPct.toFixed(2)}%</span></div>
      <div class="comparison-row">
        <div class="timing-label"><span>baseline</span><span>${formatMaybeMs(baselineMs)}</span></div>
        <div class="comparison-bar"><span class="bar-host" style="width:${barWidth(baselineMs, maxValue)}%"></span></div>
      </div>
      <div class="comparison-row">
        <div class="timing-label"><span>current</span><span>${formatMaybeMs(currentMs)}</span></div>
        <div class="comparison-bar"><span class="bar-board" style="width:${barWidth(currentMs, maxValue)}%"></span></div>
      </div>
      <div class="comparison-callout">${escapeHtml(callout)}</div>
    </article>
  `;
}

function renderComparison(snapshot) {
  const comparison = snapshot.guided_demo.comparison;
  document.getElementById("comparisonBoard").innerHTML = [
    comparisonCard(
      comparison.payload.label,
      comparison.payload.baseline_ms,
      comparison.payload.current_ms,
      comparison.payload.improvement_pct,
      comparison.payload.speedup_x,
      comparison.payload.callout
    ),
    comparisonCard(
      comparison.end_to_end.label,
      comparison.end_to_end.baseline_ms,
      comparison.end_to_end.current_ms,
      comparison.end_to_end.improvement_pct,
      comparison.end_to_end.speedup_x,
      comparison.end_to_end.callout
    ),
  ].join("");

  const notes = [];
  if (state.baselineResult) {
    notes.push(`Baseline：${state.baselineResult.source_label}，${state.baselineResult.message}`);
  }
  if (state.currentResult) {
    notes.push(`Current：${state.currentResult.source_label}，${state.currentResult.message}`);
  }
  document.getElementById("comparisonRunNote").textContent =
    notes.join(" ") || "按钮用于触发本场会话的 baseline / current 动作；条形图仍固定展示正式收口口径。";
}

function renderFault(snapshot) {
  const result = state.faultResult;
  const system = state.systemStatus;
  document.getElementById("act4Lamp").className = `act-lamp ${lampClass(result ? result.status_lamp : system.live.guard_state)}`;
  if (!result) {
    document.getElementById("faultStatusHeadline").textContent = "等待注入动作。";
    document.getElementById("faultSummary").innerHTML = [
      kpiCard("当前 guard_state", system.live.guard_state, "来自当前缓存状态或正式证据。", system.live.guard_state),
      kpiCard("last_fault_code", system.live.last_fault_code, "注入后会在此处高亮变化。", system.live.last_fault_code),
      kpiCard("FIT 汇总", "FIT-01 / FIT-02 / FIT-03", "保留原始标识，方便评委追问时核对。", "online"),
    ].join("");
    document.getElementById("faultLogPanel").textContent = "等待故障注入动作。";
  } else {
    document.getElementById("faultStatusHeadline").textContent = `${result.source_label} | ${result.message}`;
    document.getElementById("faultSummary").innerHTML = [
      kpiCard("当前动作", result.fault_type || "recover", result.source_label, result.status_lamp),
      kpiCard("guard_state", result.guard_state, "注入或恢复后的最终状态。", result.guard_state),
      kpiCard("last_fault_code", result.last_fault_code, "保留 fault code 原样便于答辩讲解。", result.last_fault_code),
    ].join("");
    document.getElementById("faultLogPanel").textContent = (result.log_entries || []).join("\n");
  }

  document.getElementById("fitGrid").innerHTML = snapshot.fits
    .map(
      (fit) => `
        <article class="fit-card">
          <div class="fit-meta">
            <span>${escapeHtml(fit.fit_id)}</span>
            <span>${escapeHtml(fit.generated_at)}</span>
          </div>
          <h3>${escapeHtml(fit.scenario)}</h3>
          <div class="status-pill ${toneClass(fit.status)}">${escapeHtml(fit.status)}</div>
          <div class="compact-copy">${escapeHtml(fit.readout)}</div>
          ${renderLinks(fit.evidence)}
        </article>
      `
    )
    .join("");
}

function renderPerformance(snapshot) {
  document.getElementById("performanceNote").textContent = snapshot.performance.positioning_note;
  document.getElementById("performanceGrid").innerHTML = snapshot.performance.metrics
    .map(
      (metric) => `
        <article class="performance-card">
          <div class="label">${escapeHtml(metric.label)}</div>
          <h3>${escapeHtml(metric.current)}</h3>
          <div class="compact-copy">baseline ${escapeHtml(metric.baseline)} | 提升 ${escapeHtml(metric.improvement)}</div>
          ${renderLinks([metric.report])}
        </article>
      `
    )
    .join("");
}

function renderSources(snapshot) {
  document.getElementById("sourcesGrid").innerHTML = snapshot.docs
    .map(
      (item) => `
        <article class="doc-card">
          <div class="label">材料</div>
          <h3>${escapeHtml(item.label)}</h3>
          <div class="compact-copy">${escapeHtml(item.path)}</div>
          <div class="link-list"><a class="doc-link" href="${docHref(item.path)}">打开</a></div>
        </article>
      `
    )
    .join("");
}

function renderActLamps(systemStatus) {
  document.getElementById("act1Lamp").className = `act-lamp ${lampClass(systemStatus.live.board_online ? "online" : systemStatus.execution_mode.tone)}`;
  if (!state.faultResult) {
    document.getElementById("act4Lamp").className = `act-lamp ${lampClass(systemStatus.live.last_fault_code)}`;
  }
}

function renderAll() {
  if (!state.snapshot || !state.systemStatus) return;
  renderTop(state.snapshot, state.systemStatus);
  renderBoardAccess(state.systemStatus);
  renderAct1(state.snapshot, state.systemStatus);
  renderSampleOptions(state.snapshot);
  renderInference(state.currentResult);
  renderComparison(state.snapshot);
  renderFault(state.snapshot);
  renderPerformance(state.snapshot);
  renderSources(state.snapshot);
  renderActLamps(state.systemStatus);
}

function switchAct(actId) {
  state.activeAct = actId;
  document.querySelectorAll(".act-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.act === actId);
  });
  document.querySelectorAll(".act-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${actId}Panel`);
  });
}

async function refreshAll() {
  const [snapshot, systemStatus] = await Promise.all([
    fetchJSON("/api/snapshot"),
    fetchJSON("/api/system-status"),
  ]);
  state.snapshot = snapshot;
  state.systemStatus = systemStatus;
  renderAll();
}

async function saveBoardAccess() {
  const payload = {
    host: document.getElementById("hostInput").value.trim(),
    user: document.getElementById("userInput").value.trim(),
    password: document.getElementById("passwordInput").value,
    port: document.getElementById("portInput").value.trim(),
    env_file: document.getElementById("envFileInput").value.trim(),
  };
  try {
    const result = await fetchJSON("/api/session/board-access", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const boardAccess = result.board_access || {};
    const onlyPasswordMissing =
      (boardAccess.missing_connection_fields || []).length === 1 &&
      boardAccess.missing_connection_fields[0] === "password";
    setFeedback(
      onlyPasswordMissing
        ? "预载的主机、端口与推理 env 已保留；补上密码后即可复用真机动作。"
        : "板卡会话已保存到当前 demo 进程内，后续探板/推理/故障动作会直接复用。",
      onlyPasswordMissing ? "warning" : "success"
    );
    document.getElementById("passwordInput").value = "";
    state.systemStatus = {
      ...state.systemStatus,
      board_access: boardAccess,
    };
    await refreshAll();
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

async function probeBoard() {
  try {
    setFeedback("正在探测板卡与 OpenAMP 状态...", "warning");
    await fetchJSON("/api/probe-board", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await refreshAll();
    setFeedback("板卡探测已完成。", "success");
    switchAct("act1");
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

async function runCurrentInference() {
  try {
    setFeedback("正在执行 Current 重建动作...", "warning");
    state.selectedImageIndex = Number(document.getElementById("imageSelect").value || 0);
    state.currentResult = await fetchJSON("/api/run-inference", {
      method: "POST",
      body: JSON.stringify({ image_index: state.selectedImageIndex, mode: "current" }),
    });
    await refreshAll();
    renderInference(state.currentResult);
    renderComparison(state.snapshot);
    setFeedback(state.currentResult.message, state.currentResult.execution_mode === "live" ? "success" : "warning");
    switchAct("act2");
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

async function runBaseline() {
  try {
    setFeedback("正在执行 Baseline 动作...", "warning");
    state.selectedImageIndex = Number(document.getElementById("imageSelect").value || 0);
    state.baselineResult = await fetchJSON("/api/run-baseline", {
      method: "POST",
      body: JSON.stringify({ image_index: state.selectedImageIndex }),
    });
    await refreshAll();
    renderComparison(state.snapshot);
    setFeedback(state.baselineResult.message, state.baselineResult.execution_mode === "live" ? "success" : "warning");
    switchAct("act3");
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

async function runAllComparisons() {
  await runBaseline();
  await runCurrentInference();
  switchAct("act3");
}

async function injectFault(faultType) {
  try {
    setFeedback("正在执行故障注入动作...", "warning");
    state.faultResult = await fetchJSON("/api/inject-fault", {
      method: "POST",
      body: JSON.stringify({ fault_type: faultType }),
    });
    await refreshAll();
    renderFault(state.snapshot);
    setFeedback(state.faultResult.message, state.faultResult.execution_mode === "live" ? "success" : "warning");
    switchAct("act4");
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

async function recoverFault() {
  try {
    setFeedback("正在执行 SAFE_STOP 恢复...", "warning");
    state.faultResult = await fetchJSON("/api/recover", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await refreshAll();
    renderFault(state.snapshot);
    setFeedback(state.faultResult.message, state.faultResult.execution_mode === "live" ? "success" : "warning");
    switchAct("act4");
  } catch (error) {
    setFeedback(error.message, "error");
  }
}

function bindEvents() {
  document.getElementById("reloadButton").addEventListener("click", () => {
    refreshAll().catch((error) => setFeedback(error.message, "error"));
  });
  document.getElementById("probeButton").addEventListener("click", () => {
    probeBoard();
  });
  document.getElementById("saveAccessButton").addEventListener("click", () => {
    saveBoardAccess();
  });
  document.getElementById("runCurrentButton").addEventListener("click", () => {
    runCurrentInference();
  });
  document.getElementById("runBaselineButton").addEventListener("click", () => {
    runBaseline();
  });
  document.getElementById("runCurrentAgainButton").addEventListener("click", () => {
    runCurrentInference();
  });
  document.getElementById("runAllButton").addEventListener("click", () => {
    runAllComparisons();
  });
  document.getElementById("recoverButton").addEventListener("click", () => {
    recoverFault();
  });

  document.querySelectorAll(".act-tab").forEach((tab) => {
    tab.addEventListener("click", () => switchAct(tab.dataset.act));
  });
  document.querySelectorAll("[data-fault]").forEach((button) => {
    button.addEventListener("click", () => injectFault(button.dataset.fault));
  });
  document.getElementById("imageSelect").addEventListener("change", (event) => {
    state.selectedImageIndex = Number(event.target.value || 0);
  });
}

async function bootstrap() {
  bindEvents();
  await refreshAll();
  switchAct(state.activeAct);
}

bootstrap().catch((error) => {
  setFeedback(error.message, "error");
});
