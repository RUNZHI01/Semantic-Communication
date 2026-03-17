const state = {
  snapshot: null,
  systemStatus: null,
  activeAct: "act1",
  selectedImageIndex: 0,
  currentResult: null,
  baselineResult: null,
  faultResult: null,
  activeInferenceJobId: null,
  activeInferenceVariant: "",
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
  const admission = systemStatus.live?.admission || {};
  const currentSupport = systemStatus.live?.variant_support?.current || {};
  const baselineSupport = systemStatus.live?.variant_support?.baseline || {};
  const latestLive = snapshot.latest_live_status || {};
  const currentSummary = currentSupport.note
    ? ` 第二幕使用 ${currentSupport.label || "Current live"}。${currentSupport.note}`
    : " 第二幕展示 Current live。";
  const baselineSummary = baselineSupport.note
    ? ` 第三幕基线：${baselineSupport.note}`
    : " 第三幕展示 formal baseline 对比。";
  const admissionSuffix = admission.mode === "signed_manifest_v1"
    ? ` 当前 live 预检已切到 signed manifest，key_id=${admission.key_id || "unknown"}.`
    : "";
  document.getElementById("heroSummary").textContent =
    `${latestLive.hero_summary || ""} trusted current SHA ${snapshot.project.trusted_current_sha.slice(0, 12)} 已与当前演示材料对齐。` +
    ` 第一幕展示板卡状态。${currentSummary}${baselineSummary} 第四幕保留 FIT-01 / FIT-02 / FIT-03 证据。` +
    admissionSuffix;

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

function renderLatestLiveStatus(snapshot) {
  const latest = snapshot.latest_live_status;
  if (!latest) return;
  const links = latest.links || [latest.report, latest.probe].filter(Boolean);
  document.getElementById("latestLiveStatusCard").innerHTML = `
    <div class="label">最新 demo 结论</div>
    <div class="inline-actions">
      <div class="mini-title">${escapeHtml(latest.headline)}</div>
      <div class="status-pill tone-online">${escapeHtml(latest.status_label)}</div>
    </div>
    <p class="compact-copy">${escapeHtml(latest.summary)}</p>
    <div class="status-meta">
      <span>收口时间=${escapeHtml(latest.as_of)}</span>
      <span>唯一实例=${escapeHtml(latest.valid_instance)}</span>
      <span>${escapeHtml(latest.current.label)}=${escapeHtml(latest.current.completed)}</span>
      <span>${escapeHtml(latest.baseline.label)}=${escapeHtml(latest.baseline.completed)}</span>
    </div>
    <div class="metric-strip">
      ${statCard("有效实例", latest.valid_instance, "当前唯一有效 live demo 实例")}
      ${statCard(latest.current.label, latest.current.completed, latest.current.note)}
      ${statCard(latest.baseline.label, latest.baseline.completed, latest.baseline.note)}
      ${statCard(latest.board.label, latest.board.value, latest.board.note)}
    </div>
    <ul class="list-plain">
      ${latest.facts.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
    <p class="compact-copy">${escapeHtml(latest.boundary_note)}</p>
    ${renderLinks(links)}
  `;
}

function renderBoardAccess(systemStatus) {
  const access = systemStatus.board_access;
  const baselineSupport = systemStatus.live?.variant_support?.baseline || {};
  const defaults = access.preloaded_defaults || {};
  const currentMissing = access.missing_inference_fields_by_variant?.current || access.missing_inference_fields || [];
  const baselineMissing = access.missing_inference_fields_by_variant?.baseline || [];
  const baselineReadiness = access.inference_ready_variants?.baseline ? "已就绪" : `仍缺 ${summarizeMissing(baselineMissing)}`;
  const baselineSummary = baselineSupport.mode === "pytorch_reference"
    ? `${baselineSupport.label || "PyTorch 参考基线"}：已归档，无需 live 会话。`
    : `Baseline：${baselineReadiness}。`;
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
      ${escapeHtml(baselineSummary)}
    </div>
    ${sourceNotes.length ? `<div class="credential-note">${escapeHtml(sourceNotes.join(" ｜ "))}</div>` : ""}
  `;
}

function renderAct1(snapshot, systemStatus) {
  const live = systemStatus.live;
  const admission = live.admission || {};
  const currentSupport = live.variant_support?.current || {};
  const baselineSupport = live.variant_support?.baseline || {};
  document.getElementById("act1StatusNote").textContent = live.status_note;
  document.getElementById("act1StatusGrid").innerHTML = [
    kpiCard("飞腾派 / SSH", live.board_online ? "在线" : "未在线", live.board_online ? "当前演示进程已拿到最新只读读数。" : "尚无新的在线读数，回退到证据。", live.board_online ? "online" : "offline"),
    kpiCard("OpenAMP / remoteproc", live.remoteproc_state, `RPMsg 设备：${live.rpmsg_device}`, live.remoteproc_state),
    kpiCard("guard_state", live.guard_state, `last_fault_code：${live.last_fault_code}`, live.guard_state),
    kpiCard("运行目标", live.target, `runtime：${live.runtime}`, "online"),
    kpiCard("准入策略", admission.label || "Legacy SHA allowlist", admission.note || "当前 live 准入配置。", admission.tone || "neutral"),
    kpiCard("Current live", currentSupport.label || "Current live", currentSupport.note || "Current 路径状态。", currentSupport.tone || "neutral"),
    kpiCard(baselineSupport.mode === "pytorch_reference" ? "基线来源" : "Baseline live", baselineSupport.label || "Baseline live", baselineSupport.note || "Baseline 路径状态。", baselineSupport.tone || "neutral"),
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

function clampPercent(value) {
  const percent = Number(value || 0);
  if (Number.isNaN(percent)) return 0;
  return Math.max(0, Math.min(100, percent));
}

function progressSourceLabel(source) {
  const labels = {
    "runner_log.missing": "未生成 runner 日志",
    "runner_log.sample_latency_lines": "实时 runner 日志",
    "runner_summary.processed_count": "最终 runner 汇总",
    pytorch_reference_manifest: "PyTorch 参考 manifest",
    demo_default: "演示默认值",
  };
  return labels[source] || "实时状态";
}

function progressAxisLabels(expectedCount) {
  const total = Math.max(Number(expectedCount || 0), 0);
  const ticks = total > 0 ? [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(total * ratio)) : [0, 25, 50, 75, 100];
  if (ticks.length === 5) ticks[4] = total > 0 ? total : 100;
  return ticks
    .map((tick) => `<span>${escapeHtml(String(tick))}</span>`)
    .join("");
}

function normalizeProgress(progress) {
  const expectedCount = Math.max(Number(progress?.expected_count || 300), 0) || 300;
  const completedCount = Math.max(Number(progress?.completed_count || 0), 0);
  const remainingCount = progress?.remaining_count !== undefined
    ? Math.max(Number(progress.remaining_count || 0), 0)
    : Math.max(expectedCount - completedCount, 0);
  const percent = progress?.percent !== undefined
    ? clampPercent(progress.percent)
    : clampPercent(expectedCount > 0 ? (completedCount / expectedCount) * 100 : 0);
  return {
    state: progress?.state || "idle",
    label: progress?.label || "等待触发",
    tone: progress?.tone || "neutral",
    percent,
    phase_percent: clampPercent(progress?.phase_percent || 0),
    completed_count: completedCount,
    expected_count: expectedCount,
    remaining_count: remainingCount,
    completion_ratio: Number(progress?.completion_ratio || 0),
    count_source: progress?.count_source || "",
    count_label: progress?.count_label || `${completedCount} / ${expectedCount}`,
    current_stage: progress?.current_stage || "等待触发",
    stages: progress?.stages || [],
    event_log: progress?.event_log || [],
  };
}

function renderProgressFrame(progress, ids, metaText) {
  const normalized = normalizeProgress(progress);
  const badge = document.getElementById(ids.badgeId);
  const count = document.getElementById(ids.countId);
  const bar = document.getElementById(ids.barId);
  const marker = document.getElementById(ids.markerId);
  const axis = document.getElementById(ids.axisId);
  const stage = ids.stageId ? document.getElementById(ids.stageId) : null;
  const meta = ids.metaId ? document.getElementById(ids.metaId) : null;

  badge.className = `status-pill ${toneClass(normalized.tone || normalized.label)}`;
  badge.textContent = normalized.label;
  count.textContent = normalized.count_label;
  bar.style.width = `${normalized.percent}%`;
  marker.style.left = `${normalized.percent}%`;
  marker.style.opacity = normalized.percent > 0 || normalized.completed_count > 0 ? "1" : "0";
  axis.innerHTML = progressAxisLabels(normalized.expected_count);
  if (stage) stage.textContent = `当前阶段：${normalized.current_stage}`;
  if (meta) meta.textContent = metaText;
  return normalized;
}

function buildProgressMeta(progress) {
  if (progress.state === "idle") {
    return `等待本场 ${progress.expected_count} 张图 live run。`;
  }
  return `计数来源：${progressSourceLabel(progress.count_source)} ｜ 当前阶段：${progress.current_stage} ｜ 剩余 ${progress.remaining_count} 张`;
}

function buildCompactProgressMeta(progress, result) {
  if (!result) {
    return "尚未开始 live run。";
  }
  const modeLabel = result.execution_mode === "live"
    ? "真实在线"
    : result.execution_mode === "reference"
      ? "PyTorch 参考基线"
      : "已回退归档样例";
  return `${modeLabel} ｜ 计数来源：${progressSourceLabel(progress.count_source)} ｜ 剩余 ${progress.remaining_count} 张`;
}

function renderLiveProgress(progress) {
  const normalized = renderProgressFrame(
    progress,
    {
      badgeId: "liveProgressBadge",
      countId: "liveProgressCount",
      barId: "liveProgressBar",
      markerId: "liveProgressMarker",
      axisId: "liveProgressAxis",
      metaId: "liveProgressMeta",
    },
    buildProgressMeta(normalizeProgress(progress))
  );
  const badge = document.getElementById("liveProgressBadge");
  const chips = document.getElementById("liveStageChips");
  const trace = document.getElementById("liveTracePanel");

  if (!progress) {
    badge.className = "status-pill tone-neutral";
    chips.innerHTML = "";
    trace.textContent = "等待板端推进。";
    return;
  }
  chips.innerHTML = normalized.stages
    .map(
      (stage) => `
        <article class="stage-chip" data-status="${escapeHtml(stage.status)}">
          <span class="label">${escapeHtml(stage.label)}</span>
          <strong>${escapeHtml(stage.status === "done" ? "已完成" : stage.status === "current" ? "推进中" : stage.status === "error" ? "停在此处" : "待推进")}</strong>
          <small>${escapeHtml(stage.detail || "")}</small>
        </article>
      `
    )
    .join("");
  trace.textContent = normalized.event_log.join("\n") || "等待板端推进。";
}

function renderComparisonProgressCards() {
  const baselineDefaultProgress = state.baselineResult?.live_progress || {
    expected_count: state.snapshot?.guided_demo?.comparison?.baseline_source?.output_count || 300,
    completed_count: 0,
    count_label: `0 / ${state.snapshot?.guided_demo?.comparison?.baseline_source?.output_count || 300}`,
    label: "等待装载",
    current_stage: "等待装载 PyTorch 参考基线",
    count_source: "demo_default",
  };
  const baselineProgress = renderProgressFrame(
    baselineDefaultProgress,
    {
      badgeId: "baselineProgressBadge",
      countId: "baselineProgressCount",
      barId: "baselineProgressBar",
      markerId: "baselineProgressMarker",
      axisId: "baselineProgressAxis",
      stageId: "baselineProgressStage",
      metaId: "baselineProgressMeta",
    },
    state.baselineResult
      ? buildCompactProgressMeta(normalizeProgress(state.baselineResult?.live_progress || null), state.baselineResult)
      : "尚未加载参考基线。"
  );
  const currentProgress = renderProgressFrame(
    state.currentResult?.live_progress || null,
    {
      badgeId: "comparisonCurrentProgressBadge",
      countId: "comparisonCurrentProgressCount",
      barId: "comparisonCurrentProgressBar",
      markerId: "comparisonCurrentProgressMarker",
      axisId: "comparisonCurrentProgressAxis",
      stageId: "comparisonCurrentProgressStage",
      metaId: "comparisonCurrentProgressMeta",
    },
    buildCompactProgressMeta(normalizeProgress(state.currentResult?.live_progress || null), state.currentResult)
  );
  return { baselineProgress, currentProgress };
}

function renderTimingRows(stageValues, labelFormatter = (label) => label) {
  const maxValue = Math.max(...stageValues.map((item) => Number(item.value_ms || 0)), 1);
  return stageValues
    .map((item) => {
      const emphasisClass = item.emphasis === "board" ? "bar-board" : item.emphasis === "total" ? "bar-total" : "bar-host";
      return `
        <div class="timing-row">
          <div class="timing-label">
            <span>${escapeHtml(labelFormatter(item.label))}</span>
            <span>${formatMaybeMs(item.value_ms)}</span>
          </div>
          <div class="timing-bar"><span class="${emphasisClass}" style="width:${barWidth(Number(item.value_ms || 0), maxValue)}%"></span></div>
        </div>
      `;
    })
    .join("");
}

function renderInference(result) {
  if (!result) {
    document.getElementById("act2SourceLabel").textContent = "等待执行。";
    document.getElementById("timingBoard").innerHTML = "";
    document.getElementById("qualityMetrics").innerHTML = "";
    document.getElementById("inferenceMessage").textContent = "等待触发重建。";
    renderLiveProgress(null);
    return;
  }
  renderLiveProgress(result.live_progress || null);
  document.getElementById("act2SourceLabel").textContent = `${result.source_label} | ${result.sample.label}`;
  document.getElementById("originalImage").src = result.original_image_b64;
  document.getElementById("reconstructedImage").src = result.reconstructed_image_b64;
  document.getElementById("inferenceMessage").textContent = result.message;

  if (result.request_state === "running") {
    document.getElementById("timingBoard").innerHTML = `
      <div class="timing-row">
        <div class="timing-label">
          <span>当前阶段</span>
          <span>${escapeHtml(result.live_progress?.current_stage || "等待板端响应")}</span>
        </div>
        <div class="timing-bar"><span class="bar-board" style="width:${Math.max(6, Number(result.live_progress?.percent || 0))}%"></span></div>
      </div>
    `;
    document.getElementById("qualityMetrics").innerHTML = [
      `<div class="metric-chip">状态: ${escapeHtml(result.live_progress?.label || "真实在线推进")}</div>`,
      `<div class="metric-chip">阶段: ${escapeHtml(result.live_progress?.current_stage || "等待板端响应")}</div>`,
      `<div class="metric-chip">进度: ${escapeHtml(result.live_progress?.count_label || "0 / 300")}</div>`,
      `<div class="metric-chip">画面: 归档样例稳定展示</div>`,
    ].join("");
    return;
  }

  if (result.status === "fallback") {
    const stageValues = result.timings?.stages || [];
    const handshakeIncomplete = result.live_attempt?.control_handshake_complete === false;
    const archiveNotice = handshakeIncomplete
      ? "本次 live 未完成 STATUS_RESP/JOB_ACK 握手，以下图像与指标仅来自归档样例和正式报告。"
      : "当前画面与以下图像/指标来自归档样例和正式报告，不代表本次 live 已完成。";
    document.getElementById("timingBoard").innerHTML = `
      <div class="compact-copy">${escapeHtml(archiveNotice)}</div>
      ${renderTimingRows(stageValues, (label) => `归档参考 · ${label}`)}
    `;
    const qualityChips = [
      `<div class="metric-chip">live: ${escapeHtml(result.live_progress?.label || "已回退")}</div>`,
      `<div class="metric-chip">${escapeHtml(handshakeIncomplete ? "握手: 未完成" : "展示: 归档样例")}</div>`,
    ];
    if (result.quality?.psnr_db !== null && result.quality?.psnr_db !== undefined) {
      qualityChips.push(`<div class="metric-chip">归档 PSNR: ${Number(result.quality.psnr_db || 0).toFixed(2)} dB</div>`);
    }
    if (result.quality?.ssim !== null && result.quality?.ssim !== undefined) {
      qualityChips.push(`<div class="metric-chip">归档 SSIM: ${Number(result.quality.ssim || 0).toFixed(4)}</div>`);
    }
    document.getElementById("qualityMetrics").innerHTML = qualityChips.join("");
    return;
  }

  const stageValues = result.timings.stages || [];
  document.getElementById("timingBoard").innerHTML = renderTimingRows(stageValues);

  document.getElementById("qualityMetrics").innerHTML = [
    `<div class="metric-chip">PSNR: ${Number(result.quality.psnr_db || 0).toFixed(2)} dB</div>`,
    `<div class="metric-chip">SSIM: ${Number(result.quality.ssim || 0).toFixed(4)}</div>`,
    `<div class="metric-chip">artifact: ${escapeHtml(String(result.artifact_sha).slice(0, 12))}</div>`,
  ].join("");
}

function comparisonCard(card) {
  const baselineLabel = card.baseline_label || "baseline";
  const currentLabel = card.current_label || "current";
  const { label, baseline_ms: baselineMs, current_ms: currentMs, improvement_pct: improvementPct, speedup_x: speedupX, callout } = card;
  const maxValue = Math.max(baselineMs, currentMs, 1);
  return `
    <article class="comparison-card">
      <div class="comparison-title">${escapeHtml(label)}<span class="comparison-speedup">${speedupX.toFixed(1)}x / ${improvementPct.toFixed(2)}%</span></div>
      <div class="comparison-row">
        <div class="timing-label"><span>${escapeHtml(baselineLabel)}</span><span>${formatMaybeMs(baselineMs)}</span></div>
        <div class="comparison-bar"><span class="bar-host" style="width:${barWidth(baselineMs, maxValue)}%"></span></div>
      </div>
      <div class="comparison-row">
        <div class="timing-label"><span>${escapeHtml(currentLabel)}</span><span>${formatMaybeMs(currentMs)}</span></div>
        <div class="comparison-bar"><span class="bar-board" style="width:${barWidth(currentMs, maxValue)}%"></span></div>
      </div>
      <div class="comparison-callout">${escapeHtml(callout)}</div>
    </article>
  `;
}

function renderComparison(snapshot) {
  const comparison = snapshot.guided_demo.comparison;
  const currentSupport = state.systemStatus?.live?.variant_support?.current || {};
  const baselineSupport = state.systemStatus?.live?.variant_support?.baseline || {};
  const boardBusy = String(state.systemStatus?.live?.guard_state || "").toUpperCase() === "JOB_ACTIVE";
  renderComparisonProgressCards();
  document.getElementById("comparisonBoard").innerHTML = [
    comparisonCard(comparison.payload),
    comparisonCard(comparison.end_to_end),
  ].join("");

  const notes = [];
  if (state.baselineResult) {
    notes.push(`基线：${state.baselineResult.source_label}，${state.baselineResult.message}`);
  }
  if (state.currentResult) {
    notes.push(`Current：${state.currentResult.source_label}，${state.currentResult.message}`);
  }
  if (!state.baselineResult && baselineSupport.note) {
    notes.push(`基线：${baselineSupport.note}`);
  }
  if (!state.currentResult && currentSupport.note) {
    notes.push(`Current：${currentSupport.note}`);
  }
  if (boardBusy) {
    notes.push("板端当前 guard_state=JOB_ACTIVE；demo 会保守阻断新的 live launch，不自动 SAFE_STOP。");
  }
  document.getElementById("comparisonRunNote").textContent =
    notes.join(" ") || "Current signed live 可在线推进；第三幕基线固定使用 PyTorch 参考归档，不再尝试 Baseline TVM live。";
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
          ${renderLinks(metric.links || (metric.report ? [metric.report] : []))}
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

function applyLaunchPolicy(systemStatus) {
  const currentSupport = systemStatus.live?.variant_support?.current || {};
  const baselineSupport = systemStatus.live?.variant_support?.baseline || {};
  const baselineIsReference = baselineSupport.mode === "pytorch_reference";
  const boardBusy = String(systemStatus.live?.guard_state || "").toUpperCase() === "JOB_ACTIVE";
  const boardBusyReason = "板端当前 guard_state=JOB_ACTIVE；demo 保守阻断新的 live launch，不自动 SAFE_STOP。";
  const currentBlocked = boardBusy || currentSupport.launch_allowed === false;
  const baselineBlocked = baselineIsReference ? false : (boardBusy || baselineSupport.launch_allowed === false);

  const currentButton = document.getElementById("runCurrentButton");
  const currentAgainButton = document.getElementById("runCurrentAgainButton");
  const baselineButton = document.getElementById("runBaselineButton");
  const runAllButton = document.getElementById("runAllButton");

  const currentLabel = currentSupport.mode === "signed_manifest_v1"
    ? "启动 Current signed 300 张图在线推进"
    : "启动 Current 300 张图在线推进";
  currentButton.textContent = currentLabel;
  currentAgainButton.textContent = currentSupport.mode === "signed_manifest_v1"
    ? "运行 Current signed 300 张图"
    : "运行 Current 300 张图";
  baselineButton.textContent = baselineIsReference
    ? (baselineSupport.action_label || "加载 PyTorch 参考基线")
    : baselineSupport.launch_allowed === false
      ? "Baseline live 未适配 signed admission"
      : "运行 Baseline 300 张图";
  runAllButton.textContent = baselineIsReference
    ? "加载参考基线 + 运行 Current live"
    : baselineSupport.launch_allowed === false
      ? "双版本 live 当前未开放"
      : "一键顺序运行双版本 300 张图";

  currentButton.disabled = currentBlocked;
  currentAgainButton.disabled = currentBlocked;
  baselineButton.disabled = baselineBlocked;
  runAllButton.disabled = currentBlocked || (!baselineIsReference && baselineBlocked);

  currentButton.title = boardBusy ? boardBusyReason : (currentSupport.note || "");
  currentAgainButton.title = currentButton.title;
  baselineButton.title = baselineSupport.note || "";
  runAllButton.title = boardBusy ? boardBusyReason : (currentBlocked ? (currentSupport.note || "") : (baselineSupport.note || ""));
}

function renderAll() {
  if (!state.snapshot || !state.systemStatus) return;
  renderTop(state.snapshot, state.systemStatus);
  renderLatestLiveStatus(state.snapshot);
  renderBoardAccess(state.systemStatus);
  renderAct1(state.snapshot, state.systemStatus);
  renderSampleOptions(state.snapshot);
  renderInference(state.currentResult);
  renderComparison(state.snapshot);
  renderFault(state.snapshot);
  renderPerformance(state.snapshot);
  renderSources(state.snapshot);
  renderActLamps(state.systemStatus);
  applyLaunchPolicy(state.systemStatus);
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

async function pollInferenceJob(jobId, variant) {
  state.activeInferenceJobId = jobId;
  state.activeInferenceVariant = variant;
  while (true) {
    const result = await fetchJSON(`/api/inference-progress?job_id=${encodeURIComponent(jobId)}`);
    if (variant === "baseline") {
      state.baselineResult = result;
    } else {
      state.currentResult = result;
    }
    renderInference(state.currentResult);
    renderComparison(state.snapshot);
    if (result.request_state !== "running") {
      await refreshAll();
      state.activeInferenceJobId = null;
      state.activeInferenceVariant = "";
      return result;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 350));
  }
}

function feedbackToneForResult(result) {
  return result.execution_mode === "live" || result.execution_mode === "reference" ? "success" : "warning";
}

async function runInferenceAction(endpoint, variant, resultKey, actId, feedbackText) {
  try {
    setFeedback(feedbackText, "warning");
    state.selectedImageIndex = Number(document.getElementById("imageSelect").value || 0);
    const initial = await fetchJSON(endpoint, {
      method: "POST",
      body: JSON.stringify({ image_index: state.selectedImageIndex, mode: variant }),
    });
    state[resultKey] = initial;
    renderInference(state.currentResult);
    renderComparison(state.snapshot);
    switchAct(actId);
    if (initial.request_state === "running" && initial.job_id) {
      const finalResult = await pollInferenceJob(initial.job_id, variant);
      setFeedback(finalResult.message, feedbackToneForResult(finalResult));
      return finalResult;
    }
    await refreshAll();
    setFeedback(initial.message, feedbackToneForResult(initial));
    return initial;
  } catch (error) {
    setFeedback(error.message, "error");
    throw error;
  }
}

async function runCurrentInference() {
  state.currentResult = await runInferenceAction(
    "/api/run-inference",
    "current",
    "currentResult",
    "act2",
    "正在执行 Current 在线推进..."
  );
}

async function runBaseline() {
  state.baselineResult = await runInferenceAction(
    "/api/run-baseline",
    "baseline",
    "baselineResult",
    "act3",
    "正在加载 PyTorch 参考基线..."
  );
}

async function runAllComparisons() {
  switchAct("act3");
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
    setFeedback("正在执行 SAFE_STOP 收口...", "warning");
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
