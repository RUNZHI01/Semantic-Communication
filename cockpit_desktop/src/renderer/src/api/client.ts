import type {
  AircraftPositionResponse,
  ArchiveSessionDetail,
  ArchiveSessionsResponse,
  BoardAccessPayload,
  BoardAccessResponse,
  DemoSnapshot,
  EventSpineResponse,
  FaultInjectResponse,
  GatePreviewResponse,
  HealthResponse,
  LinkDirectorStatus,
  LinkDirectorSwitchResponse,
  ProbeBoardResponse,
  RecoverResponse,
  RunInferenceResponse,
  SystemStatusResponse,
} from './types'

/** Vite dev server proxies /api → Python；生产直连本机（CORS 已开）。 */
const API_PREFIX = import.meta.env.DEV ? '' : 'http://127.0.0.1:8079'

async function readJson<T>(response: Response): Promise<T> {
  return (await response.json()) as T
}

function throwIfNotOk(response: Response, body: unknown): void {
  if (response.ok) return
  let message = `HTTP ${response.status}`
  if (typeof body === 'object' && body !== null && 'message' in body) {
    message = String((body as { message?: unknown }).message ?? message)
  }
  throw new Error(message)
}

async function postJson<T>(url: string, body: unknown = {}): Promise<T> {
  const response = await fetch(`${API_PREFIX}${url}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await readJson<T & { message?: string }>(response)
  throwIfNotOk(response, data)
  return data
}

// ---------------------------------------------------------------------------
// GET
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  const r = await fetch(`${API_PREFIX}/api/health`)
  const d = await readJson<HealthResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  const r = await fetch(`${API_PREFIX}/api/system-status`)
  const d = await readJson<SystemStatusResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getSnapshot(): Promise<DemoSnapshot> {
  const r = await fetch(`${API_PREFIX}/api/snapshot`)
  const d = await readJson<DemoSnapshot & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getAircraftPosition(): Promise<AircraftPositionResponse> {
  const r = await fetch(`${API_PREFIX}/api/aircraft-position`)
  const d = await readJson<AircraftPositionResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getLinkDirector(): Promise<LinkDirectorStatus> {
  const r = await fetch(`${API_PREFIX}/api/link-director`)
  const d = await readJson<LinkDirectorStatus & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getEventSpine(limit = 25): Promise<EventSpineResponse> {
  const r = await fetch(`${API_PREFIX}/api/event-spine?limit=${limit}`)
  const d = await readJson<EventSpineResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getArchiveSessions(limit = 25): Promise<ArchiveSessionsResponse> {
  const r = await fetch(`${API_PREFIX}/api/archive/sessions?limit=${limit}`)
  const d = await readJson<ArchiveSessionsResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getArchiveSession(sessionId: string, limit = 25): Promise<ArchiveSessionDetail> {
  const r = await fetch(`${API_PREFIX}/api/archive/session?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`)
  const d = await readJson<ArchiveSessionDetail & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

export async function getInferenceProgress(jobId: string): Promise<RunInferenceResponse> {
  const r = await fetch(`${API_PREFIX}/api/inference-progress?job_id=${encodeURIComponent(jobId)}`)
  const d = await readJson<RunInferenceResponse & { message?: string }>(r)
  throwIfNotOk(r, d)
  return d
}

// ---------------------------------------------------------------------------
// POST — actions
// ---------------------------------------------------------------------------

export async function postProbeBoard(): Promise<ProbeBoardResponse> {
  return postJson<ProbeBoardResponse>('/api/probe-board')
}

export async function postRunInference(imageIndex = 0, variant = 'current'): Promise<RunInferenceResponse> {
  return postJson<RunInferenceResponse>('/api/run-inference', { image_index: imageIndex, mode: variant })
}

export async function postRunBaseline(imageIndex = 0): Promise<RunInferenceResponse> {
  return postJson<RunInferenceResponse>('/api/run-baseline', { image_index: imageIndex })
}

export async function postInjectFault(faultType: string): Promise<FaultInjectResponse> {
  return postJson<FaultInjectResponse>('/api/inject-fault', { fault_type: faultType })
}

export async function postRecover(): Promise<RecoverResponse> {
  return postJson<RecoverResponse>('/api/recover')
}

export async function postLinkDirectorProfile(profileId: string): Promise<LinkDirectorSwitchResponse> {
  return postJson<LinkDirectorSwitchResponse>('/api/link-director/profile', { profile_id: profileId })
}

export async function postBoardAccess(payload: BoardAccessPayload): Promise<{ status: string; board_access: BoardAccessResponse }> {
  return postJson('/api/session/board-access', payload)
}

export async function postJobManifestGatePreview(variant = 'current'): Promise<GatePreviewResponse> {
  return postJson<GatePreviewResponse>('/api/job-manifest-gate/preview', { variant })
}
