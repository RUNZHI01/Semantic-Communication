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
  if (normalized.includes("pass") || normalized.includes("live")) return "tone-pass";
  if (normalized.includes("fail")) return "tone-fail";
  if (normalized.includes("fallback") || normalized.includes("warning")) return "tone-warning";
  return "tone-neutral";
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
    "Last proven board state",
    evidence.label,
    evidence.summary,
    [
      `remoteproc=${transport.remoteproc_state || "unknown"}`,
      `rpmsg=${transport.rpmsg_dev || "unknown"}`,
      `wrapper=${evidence.wrapper_board_smoke.result}`,
      `firmware=${evidence.final_live_firmware_sha256.slice(0, 12)}`,
      `confirmed=${evidence.confirmed_at}`,
    ],
    evidence.evidence
  );

  const current = snapshot.board.current_status;
  const details = current.details || {};
  const remoteproc = (details.remoteproc || [])
    .map((item) => `${item.name}=${item.state}`)
    .join(", ");
  document.getElementById("boardLiveCard").innerHTML = boardStatusCard(
    "Current live read",
    current.reachable ? "Live probe OK" : "Fallback only",
    current.summary,
    [
      current.requested_at ? `requested=${current.requested_at}` : "requested=not yet",
      remoteproc ? remoteproc : "remoteproc=not available",
      details.firmware && details.firmware.sha256 ? `sha=${details.firmware.sha256.slice(0, 12)}` : "sha=not available",
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
    <div class="label">Host Side</div>
    <div class="readout">${escapeHtml(host.summary)}</div>
    ${renderLinks(host.items)}
  `;

  const slave = snapshot.operator.slave_side;
  document.getElementById("slaveSideCard").innerHTML = `
    <div class="label">Slave / OpenAMP Side</div>
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
          <div class="status-pill ${toneClass(item.status)}">${escapeHtml(item.status)}</div>
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
            <div class="label">Historical trail</div>
            <div class="status-pill ${toneClass(fit.history.status)}">${escapeHtml(fit.history.status)}</div>
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
          <div class="status-pill ${toneClass(fit.status)}">${escapeHtml(fit.status)}</div>
          <div class="readout">${escapeHtml(fit.readout)}</div>
          <ul class="list-plain">
            <li><strong>Risk:</strong> ${escapeHtml(fit.risk_item)}</li>
            <li><strong>Trusted current:</strong> ${escapeHtml(fit.trusted_current_sha.slice(0, 12))}</li>
            ${fit.live_firmware_sha256 ? `<li><strong>Firmware:</strong> ${escapeHtml(fit.live_firmware_sha256.slice(0, 12))}</li>` : ""}
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
          <div class="readout">baseline ${escapeHtml(metric.baseline)} | improvement ${escapeHtml(metric.improvement)}</div>
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
          <div class="label">Source</div>
          <h3>${escapeHtml(item.label)}</h3>
          <div class="readout">${escapeHtml(item.path)}</div>
          <div class="link-list">
            <a class="doc-link" href="${docHref(item.path)}">Open</a>
          </div>
        </article>
      `
    )
    .join("");
}

function renderTop(snapshot) {
  document.getElementById("heroSummary").textContent =
    `${snapshot.project.final_verdict}. Trusted current ${snapshot.project.trusted_current_sha.slice(0, 12)} is aligned to the demo evidence and the latest performance readout.`;
  document.getElementById("modePill").className = `mode-pill ${toneClass(snapshot.mode.effective_tone)}`;
  document.getElementById("modePill").textContent = snapshot.mode.effective_label;
  document.getElementById("modeSummary").textContent = `${snapshot.mode.summary} Policy: ${snapshot.mode.live_policy}`;
  document.getElementById("generatedAt").textContent = `snapshot ${snapshot.generated_at}`;
  document.getElementById("topStats").innerHTML = [
    statCard("P0 milestones", String(snapshot.stats.p0_milestones_verified), "board-backed items in the dashboard"),
    statCard("FIT final pass", String(snapshot.stats.fit_final_pass_count), "formal FIT entries closed"),
    statCard("Payload median", `${snapshot.stats.payload_current_ms} ms`, "trusted current SHA"),
    statCard("End-to-end", `${snapshot.stats.end_to_end_current_ms} ms/image`, "trusted current SHA"),
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
  button.textContent = "Probing...";
  try {
    const response = await fetch("/api/probe-board", { method: "POST" });
    if (!response.ok) throw new Error(`probe request failed: ${response.status}`);
    await loadSnapshot();
  } finally {
    button.disabled = false;
    button.textContent = "Refresh live board status";
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
