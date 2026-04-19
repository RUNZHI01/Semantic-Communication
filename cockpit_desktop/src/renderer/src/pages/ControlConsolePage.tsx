import { useState, useEffect, useRef } from 'react'
import { useCryptoStatus } from '../hooks/useCryptoStatus'
import { useInjectFault, useRecover, useProbeBoard, useSwitchLinkProfile } from '../hooks/useActions'
import { getEventSpine } from '../api/client'
import { PageTransition, StaggeredList, AnimatedListItem } from '../components/animations'
import { Icons } from '../components/icons'
import s from './ControlConsolePage.module.css'
// Server event spine returns { recent_events: [...], aggregate: { event_count } }
type SpineEvent = { type?: string; timestamp?: string; message?: string; source?: string; plane?: string; data?: Record<string, unknown> }

/* ── Protocol capability checklist ── */

const PROTOCOL_CHECKLIST = [
  { label: 'JOB_REQ / JOB_ACK / JOB_DONE', status: 'ok' as const },
  { label: 'HEARTBEAT / HEARTBEAT_ACK', status: 'ok' as const },
  { label: 'STATUS_REQ / STATUS_RESP', status: 'ok' as const },
  { label: 'SAFE_STOP → STATUS_RESP', status: 'ok' as const },
  { label: 'SIGNED_ADMISSION (4 阶段)', status: 'ok' as const },
  { label: 'LINK_HEALTH → MODE_DIRECTIVE', status: 'ok' as const },
  { label: 'rx_locked=0 → SAFE_STOP', status: 'ok' as const },
] as const

/* ── FIT scenario definitions ── */

const FIT_SCENARIOS = [
  {
    id: 'wrong_sha',
    label: 'FIT-01：SHA 篡改',
    desc: '注入错误 SHA256 → JOB_ACK(DENY, ARTIFACT_SHA)',
    icon: Icons.AlertTriangle,
  },
  {
    id: 'heartbeat_timeout',
    label: 'FIT-02：心跳超时',
    desc: '中断心跳 → watchdog 触发 SAFE_STOP',
    icon: Icons.Clock,
  },
  {
    id: 'illegal_param',
    label: 'FIT-03：非法参数',
    desc: '发送越界参数 → JOB_ACK(DENY, PARAM_RANGE)',
    icon: Icons.XCircle,
  },
] as const

/* ── Mode definitions ── */

const MODE_CARDS = [
  {
    profile: 'normal',
    mode: 'FULL_FRAME',
    label: '全图模式',
    desc: '完整张量传输 · 300 张全量推理',
    tone: 'ok' as const,
  },
  {
    profile: 'lossy',
    mode: 'ROI_ONLY',
    label: 'ROI 降采样',
    desc: '跳帧 3:1 · 有效推理 100 张',
    tone: 'warn' as const,
  },
  {
    profile: 'flaky',
    mode: 'ALERT_ONLY',
    label: '告警模式',
    desc: '推理挂起 · 仅传输北斗坐标',
    tone: 'danger' as const,
  },
] as const

const TONE_CLS: Record<string, string> = {
  ok: s.modeCardOk,
  warn: s.modeCardWarn,
  danger: s.modeCardDanger,
}

/* ── Helper: format event type color ── */

function eventBadgeCls(eventType: string): string {
  if (eventType.includes('SAFE_STOP') || eventType.includes('LOST') || eventType.includes('REJECTED')) return s.evtBadgeDanger
  if (eventType.includes('HEARTBEAT') || eventType.includes('ROI') || eventType.includes('COORD')) return s.evtBadgeWarn
  return s.evtBadgeOk
}

/* ── Page component ── */

export function ControlConsolePage() {
  const { data: cryptoData, refetch: refetchCrypto } = useCryptoStatus()
  const faultMut = useInjectFault()
  const recoverMut = useRecover()
  const probeMut = useProbeBoard()
  const switchMut = useSwitchLinkProfile()

  const currentMode = cryptoData?.service_mode?.current_mode ?? 'FULL_FRAME'

  // ── Event spine polling ──
  const [events, setEvents] = useState<SpineEvent[]>([])
  const [eventCount, setEventCount] = useState(0)
  const timelineRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const data = await getEventSpine(20) as Record<string, unknown>
        const recentEvents = (data.recent_events ?? []) as SpineEvent[]
        if (!cancelled && recentEvents.length > 0) {
          setEvents(recentEvents)
          setEventCount((data.aggregate as Record<string, unknown>)?.event_count as number ?? recentEvents.length)
        }
      } catch { /* ignore */ }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  // Auto-scroll timeline to bottom
  useEffect(() => {
    if (timelineRef.current) {
      timelineRef.current.scrollTop = timelineRef.current.scrollHeight
    }
  }, [events])

  // ── FIT injection with auto refetch ──
  const handleFIT = (fitId: string) => {
    faultMut.mutate(fitId, {
      onSuccess: (data) => {
        refetchCrypto()
        // Trigger event spine refresh
        getEventSpine(20).then(d => { const r = d as Record<string, unknown>; const e = (r.recent_events ?? []) as SpineEvent[]; if (e.length) { setEvents(e); setEventCount((r.aggregate as Record<string, unknown>)?.event_count as number ?? e.length) }}).catch(() => {})
        // Show result in a non-blocking way
        const guardState = data?.guard_state ?? 'UNKNOWN'
        const faultCode = data?.last_fault_code ?? 'UNKNOWN'
        setActionLog(prev => [...prev.slice(-4), `[FIT] ${fitId} → guard=${guardState} fault=${faultCode} (${data?.execution_mode ?? 'unknown'})`])
      },
    })
  }

  const handleRecover = () => {
    recoverMut.mutate(undefined, {
      onSuccess: (data) => {
        refetchCrypto()
        getEventSpine(20).then(d => { const r = d as Record<string, unknown>; const e = (r.recent_events ?? []) as SpineEvent[]; if (e.length) { setEvents(e); setEventCount((r.aggregate as Record<string, unknown>)?.event_count as number ?? e.length) }}).catch(() => {})
        setActionLog(prev => [...prev.slice(-4), `[RECOVER] guard=${data?.guard_state ?? '?'} fault=${data?.last_fault_code ?? '?'} (${data?.execution_mode ?? '?'})`])
      },
    })
  }

  const handleProbe = () => {
    probeMut.mutate(undefined, {
      onSuccess: () => {
        refetchCrypto()
        setActionLog(prev => [...prev.slice(-4), `[PROBE] 探活完成，控制面状态已刷新`])
      },
    })
  }

  const handleModeSwitch = (profileId: string, modeName: string) => {
    switchMut.mutate(profileId, {
      onSuccess: () => {
        refetchCrypto()
        getEventSpine(20).then(d => { const r = d as Record<string, unknown>; const e = (r.recent_events ?? []) as SpineEvent[]; if (e.length) { setEvents(e); setEventCount((r.aggregate as Record<string, unknown>)?.event_count as number ?? e.length) }}).catch(() => {})
        setActionLog(prev => [...prev.slice(-4), `[MODE] → ${modeName}，去仪表盘启动推理查看效果`])
      },
    })
  }

  // ── Action log (inline feedback) ──
  const [actionLog, setActionLog] = useState<string[]>([])

  return (
    <PageTransition className={s.root}>
      {/* Ambient background */}
      <div className={s.meshBackground}>
        <div className={s.meshBlob1} />
        <div className={s.meshBlob2} />
      </div>

      {/* Page header */}
      <div className={s.pageHeader}>
        <h2 className={s.pageTitle}>控制台</h2>
        <p className={s.pageSubtitle}>服务模式调度 · 故障注入测试 · 实时事件流</p>
      </div>

      {/* ── Row 1: Mode Controller (full width) ── */}
      <AnimatedListItem>
        <div className={`${s.sectionCard} ${s.fullWidth}`}>
          <div className={s.sectionTitle}>
            服务模式调度（切换后去「仪表盘」启动推理查看联动效果）
          </div>
          <div className={s.modeGrid}>
            {MODE_CARDS.map((mc) => {
              const isActive = currentMode === mc.mode
              return (
                <button
                  key={mc.profile}
                  className={`${s.modeCard} ${TONE_CLS[mc.tone]} ${isActive ? s.modeCardActive : ''}`}
                  onClick={() => handleModeSwitch(mc.profile, mc.mode)}
                  disabled={switchMut.isPending}
                >
                  <div className={s.modeCardHeader}>
                    <span className={`${s.modeDot} ${isActive ? s.modeDotActive : ''}`} />
                    <span className={s.modeCardLabel}>{mc.label}</span>
                    {isActive && <span className={s.modeActiveBadge}>当前</span>}
                  </div>
                  <div className={s.modeCardDesc}>{mc.desc}</div>
                </button>
              )
            })}
          </div>
        </div>
      </AnimatedListItem>

      {/* ── Row 2: Two-column grid ── */}
      <div className={s.grid}>
        {/* ─── Left: Control plane + FIT ─── */}
        <StaggeredList staggerDelay={0.04}>
          {/* Control plane status */}
          <AnimatedListItem>
            <div className={s.sectionCard}>
              <div className={s.sectionTitle} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>控制面状态</span>
                <button
                  className={s.btnTonal}
                  onClick={handleProbe}
                  disabled={probeMut.isPending}
                  style={{ height: '28px', padding: '0 12px', fontSize: '12px' }}
                >
                  {probeMut.isPending ? <span className={s.spinner} /> : <Icons.Radar size={14} />}
                  探活
                </button>
              </div>
              <div className={s.rowGrid}>
                <span className={s.label}>Guard 状态</span>
                <span className={s.mono}>{cryptoData?.control_guard_state ?? '—'}</span>

                <span className={s.label}>最近故障</span>
                <span className={s.mono}>{cryptoData?.control_last_fault_code ?? 'NONE'}</span>

                <span className={s.label}>心跳 / 故障计数</span>
                <span className={s.mono}>
                  {cryptoData?.control_heartbeat_ok ?? 0} / {cryptoData?.control_total_fault_count ?? 0}
                </span>

                <span className={s.label}>JOB 统计</span>
                <span className={s.mono}>
                  REQ={cryptoData?.control_job_req_count ?? 0}{' '}
                  ALLOW={cryptoData?.control_job_admit_count ?? 0}{' '}
                  DENY={cryptoData?.control_job_reject_count ?? 0}
                </span>
              </div>
            </div>
          </AnimatedListItem>

          {/* FIT */}
          <AnimatedListItem>
            <div className={s.sectionCard}>
              <div className={s.sectionTitle}>FIT 故障注入测试</div>

              <div className={s.fitGrid}>
                {FIT_SCENARIOS.map((fit) => {
                  const Icon = fit.icon
                  return (
                    <div key={fit.id} className={s.fitCard}>
                      <div className={s.fitLabel}>{fit.label}</div>
                      <div className={s.fitDesc}>{fit.desc}</div>
                      <button
                        className={s.btnDanger}
                        onClick={() => handleFIT(fit.id)}
                        disabled={faultMut.isPending}
                      >
                        {faultMut.isPending ? <span className={s.spinner} /> : <Icon size={14} />}
                        <span>注入</span>
                      </button>
                    </div>
                  )
                })}
              </div>

              <button
                className={s.btnRecover}
                onClick={handleRecover}
                disabled={recoverMut.isPending}
              >
                {recoverMut.isPending ? <span className={s.spinner} /> : <Icons.RefreshCw size={14} />}
                <span>SAFE_STOP 收口</span>
              </button>

              {/* Action feedback log */}
              {actionLog.length > 0 && (
                <div className={s.actionLogBox}>
                  {actionLog.map((line, i) => (
                    <div key={i} className={s.actionLogLine}>{line}</div>
                  ))}
                </div>
              )}
            </div>
          </AnimatedListItem>

          {/* Protocol checklist */}
          <AnimatedListItem>
            <div className={s.sectionCard}>
              <div className={s.sectionTitle}>协议能力矩阵</div>
              <div className={s.checklistGrid}>
                {PROTOCOL_CHECKLIST.map((item) => (
                  <div key={item.label} className={s.checkItem}>
                    <span className={s.badgeGreen}>✓</span>
                    <span>{item.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </AnimatedListItem>
        </StaggeredList>

        {/* ─── Right: Live event timeline ─── */}
        <StaggeredList staggerDelay={0.04}>
          <AnimatedListItem>
            <div className={`${s.sectionCard} ${s.timelineCard}`}>
              <div className={s.sectionTitle} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>实时事件流</span>
                <span className={s.eventCountBadge}>{eventCount} 事件</span>
              </div>
              <div className={s.timelineScroll} ref={timelineRef}>
                {events.length === 0 ? (
                  <div className={s.timelineEmpty}>
                    <Icons.Activity size={20} style={{ opacity: 0.3 }} />
                    <span>暂无事件 — 点击探活或注入故障生成事件</span>
                  </div>
                ) : (
                  events.map((evt, i) => (
                    <div key={`${evt.timestamp}-${i}`} className={s.timelineItem}>
                      <div className={s.timelineDot} />
                      <div className={s.timelineContent}>
                        <div className={s.timelineHeader}>
                          <span className={`${s.evtBadge} ${eventBadgeCls(evt.type ?? '')}`}>
                            {evt.type}
                          </span>
                          <span className={s.timelineTime}>
                            {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString('zh-CN', { hour12: false }) : '—'}
                          </span>
                        </div>
                        <div className={s.timelineMsg}>{evt.message}</div>
                        {evt.source && <div className={s.timelineMeta}>source: {evt.source} · plane: {evt.plane ?? '—'}</div>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </AnimatedListItem>
        </StaggeredList>
      </div>
    </PageTransition>
  )
}
