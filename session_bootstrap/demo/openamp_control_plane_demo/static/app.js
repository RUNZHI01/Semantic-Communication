const state = {
  snapshot: null,
};

function docHref(path) {
  return `/docs?path=${encodeURIComponent(path)}`;
}

function toneClass(value) {
  if (!value) return "tone-neutral";
  const normalized = value.toLowerCase();
  if (normalized === "live") return "tone-live";
  if (normalized === "fallback") return "tone-fallback";
  if (
    normalized.includes("pass") ||
    normalized.includes("live") ||
    normalized.includes("通过") ||
    normalized.includes("在线") ||
    normalized.includes("已确认")
  ) {
    return "tone-pass";
  }
  if (normalized.includes("fail") || normalized.includes("失败")) return "tone-fail";
  if (
    normalized.includes("fallback") ||
    normalized.includes("warning") ||
    normalized.includes("仅展示证据") ||
    normalized.includes("回退")
  ) {
    return "tone-warning";
  }
  return "tone-neutral";
}

function displayStatus(value) {
  const normalized = String(value || "").trim().toUpperCase();
  if (normalized === "PASS") return "通过 PASS";
  if (normalized === "FAIL") return "失败 FAIL";
  if (normalized === "PASS (FINAL)") return "最终通过 PASS";
  if (normalized === "FAIL (HISTORICAL)") return "历史失败 FAIL";
  return String(value || "");
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderLinks(links) {
  if (!links || !links.length) return "";
  return `
    <div class="inline-links">
      ${links
        .map((link) => {
          const href = link.path ? docHref(link.path) : "#";
          const label = escapeHtml(link.label);
          const title = link.note ? ` title="${escapeHtml(link.note)}"` : "";
          return `<a class="doc-link" href="${href}"${title}>${label}</a>`;
        })
        .join("")}
    </div>
  `;
}

function statCard(label, value, caption) {
  return `
    <div class="mini-metric">
      <div class="caption">${escapeHtml(label)}</div>
      <div class="value">${escapeHtml(value)}</div>
      <div class="caption">${escapeHtml(caption)}</div>
    </div>
  `;
}

function boardStatusCard(title, pillText, summary, metaItems, links) {
  return `
    <div class="status-card">
      <div class="label">${escapeHtml(title)}</div>
      <div class="status-pill ${toneClass(pillText)}">${escapeHtml(pillText)}</div>
      <div class="readout">${escapeHtml(summary)}</div>
      <div class="status-meta">
        ${metaItems.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
      </div>
      ${renderLinks(links)}
    </div>
  `;
}

function renderBoard(snapshot) {
  const evidence = snapshot.board.evidence_status;
  const transport = evidence.transport || {};
  document.getElementById("boardEvidenceCard").innerHTML = boardStatusCard(
    "最近一次已确认状态",
    evidence.label,
    evidence.summary,
    [
      `remoteproc=${transport.remoteproc_state || "未知"}`,
      `RPMsg=${transport.rpmsg_dev || "未知"}`,
      `wrapper=${evidence.wrapper_board_smoke.result}`,
      `固件 SHA=${evidence.final_live_firmware_sha256.slice(0, 12)}`,
      `确认时间=${evidence.confirmed_at}`,
    ],
    evidence.evidence
  );

  const current = snapshot.board.current_status;
  const details = current.details || {};
  const remoteproc = (details.remoteproc || [])
    .map((item) => `${item.name}=${item.state}`)
    .join(", ");
  document.getElementById("boardLiveCard").innerHTML = boardStatusCard(
    "当前板卡读数",
    current.reachable ? "在线读取正常" : "仅展示证据",
    current.summary,
    [
      current.requested_at ? `读取时间=${current.requested_at}` : "读取时间=尚未执行",
      remoteproc ? remoteproc : "remoteproc=暂不可得",
      details.firmware && details.firmware.sha256 ? `固件 SHA=${details.firmware.sha256.slice(0, 12)}` : "固件 SHA=暂不可得",
    ],
    current.evidence
  );
}

function renderLaunch(snapshot) {
  document.getElementById("launchCommands").innerHTML = snapshot.operator.launch_commands
    .map((command) => `<div class="command-row"><code>${escapeHtml(command)}</code></div>`)
    .join("");

  const host = snapshot.operator.host_side;
  document.getElementById("hostSideCard").innerHTML = `
    <div class="label">主机侧</div>
    <div class="readout">${escapeHtml(host.summary)}</div>
    ${renderLinks(host.items)}
  `;

  const slave = snapshot.operator.slave_side;
  document.getElementById("slaveSideCard").innerHTML = `
    <div class="label">板端 / OpenAMP 侧</div>
    <div class="readout">${escapeHtml(slave.summary)}</div>
    ${renderLinks(slave.items)}
  `;
}

function renderMilestones(snapshot) {
  document.getElementById("milestonesGrid").innerHTML = snapshot.milestones
    .map(
      (item) => `
        <article class="milestone-card">
          <div class="milestone-meta">
            <span>${escapeHtml(item.stage)}</span>
            <span>${escapeHtml(item.mapped_id)}</span>
          </div>
          <h3>${escapeHtml(item.coverage_item)}</h3>
          <div class="status-pill ${toneClass(item.status)}">${escapeHtml(displayStatus(item.status))}</div>
          <div class="readout">${escapeHtml(item.key_proof_point)}</div>
          ${renderLinks(item.evidence)}
        </article>
      `
    )
    .join("");
}

function renderFits(snapshot) {
  document.getElementById("fitGrid").innerHTML = snapshot.fits
    .map((fit) => {
      const history = fit.history
        ? `
          <div class="card">
            <div class="label">修复前历史</div>
            <div class="status-pill ${toneClass(fit.history.status)}">${escapeHtml(displayStatus(fit.history.status))}</div>
            <div class="readout">${escapeHtml(fit.history.summary)}</div>
            ${renderLinks(fit.history.evidence)}
          </div>
        `
        : "";
      return `
        <article class="fit-card">
          <div class="fit-meta">
            <span>${escapeHtml(fit.fit_id)}</span>
            <span>${escapeHtml(fit.generated_at)}</span>
          </div>
          <h3>${escapeHtml(fit.scenario)}</h3>
          <div class="status-pill ${toneClass(fit.status)}">${escapeHtml(displayStatus(fit.status))}</div>
          <div class="readout">${escapeHtml(fit.readout)}</div>
          <ul class="list-plain">
            <li><strong>风险点:</strong> ${escapeHtml(fit.risk_item)}</li>
            <li><strong>trusted current SHA:</strong> ${escapeHtml(fit.trusted_current_sha.slice(0, 12))}</li>
            ${fit.live_firmware_sha256 ? `<li><strong>固件 SHA:</strong> ${escapeHtml(fit.live_firmware_sha256.slice(0, 12))}</li>` : ""}
          </ul>
          ${renderLinks(fit.evidence)}
          ${history}
        </article>
      `;
    })
    .join("");
}

function improvementWidth(metric) {
  const numeric = parseFloat(String(metric.improvement).replace("%", "").replace("x", ""));
  if (Number.isNaN(numeric)) return 40;
  return Math.max(10, Math.min(100, numeric));
}

function renderPerformance(snapshot) {
  document.getElementById("performanceNote").textContent = snapshot.performance.positioning_note;
  document.getElementById("performanceGrid").innerHTML = snapshot.performance.metrics
    .map(
      (metric) => `
        <article class="performance-card">
          <div class="label">${escapeHtml(metric.label)}</div>
          <h3>${escapeHtml(metric.current)}</h3>
          <div class="readout">基线 ${escapeHtml(metric.baseline)} | 提升 ${escapeHtml(metric.improvement)}</div>
          <div class="metric-bar"><span style="width:${improvementWidth(metric)}%"></span></div>
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
          <div class="label">资料</div>
          <h3>${escapeHtml(item.label)}</h3>
          <div class="readout">${escapeHtml(item.path)}</div>
          <div class="link-list">
            <a class="doc-link" href="${docHref(item.path)}">打开</a>
          </div>
        </article>
      `
    )
    .join("");
}

function renderTop(snapshot) {
  document.getElementById("heroSummary").textContent =
    `${snapshot.project.final_verdict}。当前界面将 OpenAMP 控制面证据、FIT 收口与性能结果集中展示；trusted current SHA ${snapshot.project.trusted_current_sha.slice(0, 12)} 已与本次演示材料对齐。`;
  document.getElementById("modePill").className = `mode-pill ${toneClass(snapshot.mode.effective_tone)}`;
  document.getElementById("modePill").textContent = snapshot.mode.effective_label;
  document.getElementById("modeSummary").textContent = `${snapshot.mode.summary} 现场策略：${snapshot.mode.live_policy}`;
  document.getElementById("generatedAt").textContent = `快照时间 ${snapshot.generated_at}`;
  document.getElementById("topStats").innerHTML = [
    statCard("P0 里程碑", String(snapshot.stats.p0_milestones_verified), "看板内已展示的板级证据项"),
    statCard("FIT 最终通过", String(snapshot.stats.fit_final_pass_count), "本轮正式收口的 FIT 项"),
    statCard("Payload 中位延迟", `${snapshot.stats.payload_current_ms} ms`, "对应 trusted current SHA"),
    statCard("端到端中位延迟", `${snapshot.stats.end_to_end_current_ms} ms/image`, "对应 trusted current SHA"),
  ].join("");
}

function renderSnapshot(snapshot) {
  state.snapshot = snapshot;
  renderTop(snapshot);
  renderBoard(snapshot);
  renderLaunch(snapshot);
  renderMilestones(snapshot);
  renderFits(snapshot);
  renderPerformance(snapshot);
  renderSources(snapshot);
}

async function loadSnapshot() {
  const response = await fetch("/api/snapshot", { cache: "no-store" });
  if (!response.ok) throw new Error(`snapshot request failed: ${response.status}`);
  renderSnapshot(await response.json());
}

async function refreshProbe() {
  const button = document.getElementById("probeButton");
  button.disabled = true;
  button.textContent = "正在读取...";
  try {
    const response = await fetch("/api/probe-board", { method: "POST" });
    if (!response.ok) throw new Error(`probe request failed: ${response.status}`);
    const probe = await response.json();
    await loadSnapshot();
    if (probe.status !== "success") {
      const message = probe.summary || probe.error || "在线探板失败。";
      document.getElementById("heroSummary").textContent =
        `${message} 当前继续展示最近一次成功读数或既有证据。`;
    }
  } finally {
    button.disabled = false;
    button.textContent = "读取当前板卡状态";
  }
}

document.getElementById("reloadButton").addEventListener("click", () => {
  loadSnapshot().catch((error) => {
    document.getElementById("heroSummary").textContent = error.message;
  });
});

document.getElementById("probeButton").addEventListener("click", () => {
  refreshProbe().catch((error) => {
    document.getElementById("heroSummary").textContent = error.message;
  });
});

loadSnapshot().catch((error) => {
  document.getElementById("heroSummary").textContent = error.message;
});
