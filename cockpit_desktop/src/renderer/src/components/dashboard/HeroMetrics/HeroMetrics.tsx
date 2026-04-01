import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import { Icons } from '../../icons'
import { CountUp } from '../../shared/CountUp'
import s from './HeroMetrics.module.css'

interface HeroMetricsProps {
  system: UseQueryResult<SystemStatusResponse>
  inferenceProgress?: any
}

export function HeroMetrics({ system, inferenceProgress }: HeroMetricsProps) {
  const status = system.data
  const results = status?.recent_results
  const current = results?.['current']
  const baseline = results?.['baseline']
  const live = status?.live
  const boardOnline = live?.board_online ?? false

  const payloadCurrent = current?.timings?.payload_ms
  const payloadBaseline = baseline?.timings?.payload_ms
  const improvementPct = (payloadCurrent && payloadBaseline && payloadBaseline > 0)
    ? ((payloadBaseline - payloadCurrent) / payloadBaseline * 100)
    : null

  const progress = inferenceProgress?.data?.live_progress?.completed_count ?? 0
  const totalImages = 300
  const progressPct = totalImages > 0 ? (progress / totalImages) * 100 : 0

  return (
    <div className={s.container}>
      {/* System Status — with colored dot */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <span
            className={s.metricDot}
            style={{ background: boardOnline ? 'var(--color-success)' : 'var(--color-error)' }}
          />
          <span className={s.metricLabel}>状态</span>
        </div>
        <span className={s.metricValue} style={{ color: boardOnline ? 'var(--color-success)' : 'var(--color-error)' }}>
          {boardOnline ? 'Online' : 'Offline'}
        </span>
      </div>

      {/* Guard State */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <Icons.Shield size={11} className={s.metricIcon} aria-hidden="true" />
          <span className={s.metricLabel}>Guard</span>
        </div>
        <span className={s.metricValue}>{live?.guard_state ?? '—'}</span>
      </div>

      {/* Current Payload */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <Icons.Zap size={11} className={s.metricIcon} aria-hidden="true" />
          <span className={s.metricLabel}>Payload</span>
        </div>
        {payloadCurrent != null ? (
          <span className={`${s.metricValue} ${s.metricHighlight}`}>
            <CountUp end={payloadCurrent} decimals={1} duration={350} /> ms
          </span>
        ) : (
          <span className={s.metricValue}>—</span>
        )}
      </div>

      {/* Baseline */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <Icons.Activity size={11} className={s.metricIcon} aria-hidden="true" />
          <span className={s.metricLabel}>Baseline</span>
        </div>
        {payloadBaseline != null ? (
          <span className={s.metricValue}>
            <CountUp end={payloadBaseline} decimals={1} duration={350} /> ms
          </span>
        ) : (
          <span className={s.metricValue}>—</span>
        )}
      </div>

      {/* Improvement */}
      {improvementPct != null && (
        <div className={s.metricItem}>
          <div className={s.metricTop}>
            <Icons.TrendingUp size={11} className={s.metricIcon} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            <span className={s.metricLabel}>加速</span>
          </div>
          <span className={`${s.metricValue} ${s.metricSuccess}`}>
            <CountUp end={improvementPct} decimals={1} duration={350} />%
          </span>
        </div>
      )}

      {/* Inference Progress */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <Icons.BarChart size={11} className={s.metricIcon} aria-hidden="true" />
          <span className={s.metricLabel}>推理进度</span>
        </div>
        <div className={s.progressGroup}>
          <span className={s.metricValue}>
            <CountUp end={progress} duration={300} />/{totalImages}
          </span>
          <div className={s.miniTrack}>
            <div className={s.miniFill} style={{ width: `${progressPct}%` }} />
          </div>
        </div>
      </div>
    </div>
  )
}
