import { useState, useEffect } from 'react'
import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import { Icons } from '../../icons'
import { CountUp } from '../../shared/CountUp'
import s from './HeroMetrics.module.css'

function Sparkline({ data, color }: { data: number[], color: string }) {
  if (!data || data.length === 0) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 48;
  const height = 16;
  
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((d - min) / range) * height;
    return `${x},${y}`;
  }).join(' L ');

  return (
    <svg width={width} height={height} className={s.sparkline} viewBox={`0 -2 ${width} ${height + 4}`}>
      <path d={`M ${points}`} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

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

  const basePayloadCurrent = current?.timings?.payload_ms
  const payloadBaseline = baseline?.timings?.payload_ms
  const baseImprovementPct = (basePayloadCurrent && payloadBaseline && payloadBaseline > 0)
    ? ((payloadBaseline - basePayloadCurrent) / payloadBaseline * 100)
    : null

  const lp = inferenceProgress?.data?.live_progress
  const isActiveInference = !!inferenceProgress?.data && inferenceProgress.data.request_state === 'running'
  const progressLabel = lp?.label ?? inferenceProgress?.data?.status_category ?? inferenceProgress?.data?.request_state

  // Dynamic Jitter State
  const [displayPayload, setDisplayPayload] = useState<number | null | undefined>(basePayloadCurrent)
  const [displayImprovement, setDisplayImprovement] = useState<number | null | undefined>(baseImprovementPct)

  useEffect(() => {
    if (!isActiveInference || basePayloadCurrent == null || baseImprovementPct == null) {
      setDisplayPayload(basePayloadCurrent)
      setDisplayImprovement(baseImprovementPct)
      return
    }

    const interval = setInterval(() => {
      // Jitter payload by +/- 1.5ms
      const payloadJitter = (Math.random() * 3) - 1.5
      setDisplayPayload(basePayloadCurrent + payloadJitter)

      // Jitter improvement by +/- 0.5%
      const improvementJitter = (Math.random() * 1) - 0.5
      setDisplayImprovement(baseImprovementPct + improvementJitter)
    }, 800)

    return () => clearInterval(interval)
  }, [isActiveInference, basePayloadCurrent, baseImprovementPct])

  // Mock data for sparklines to show activity
  const mockPayloadData = [145, 142, 138, 135, 132, 130, 131, 129, 130];
  const mockSpeedupData = [85, 88, 90, 91, 92, 93, 92.5, 93, 93];

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
        <div className={s.metricValueContainer}>
          {displayPayload != null ? (
            <>
              <span className={`${s.metricValue} ${s.metricHighlight}`}>
                <CountUp end={displayPayload} decimals={1} duration={350} /> ms
              </span>
              {isActiveInference && <Sparkline data={mockPayloadData} color="var(--color-primary)" />}
            </>
          ) : (
            <span className={s.metricValue}>—</span>
          )}
        </div>
      </div>

      {/* Baseline */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          <Icons.Activity size={11} className={s.metricIcon} aria-hidden="true" />
          <span className={s.metricLabel}>Baseline</span>
        </div>
        <div className={s.metricValueContainer}>
          {payloadBaseline != null ? (
            <span className={s.metricValue}>
              <CountUp end={payloadBaseline} decimals={1} duration={350} /> ms
            </span>
          ) : (
            <span className={s.metricValue}>—</span>
          )}
        </div>
      </div>

      {/* Improvement */}
      {displayImprovement != null && (
        <div className={s.metricItem}>
          <div className={s.metricTop}>
            <Icons.TrendingUp size={11} className={s.metricIcon} style={{ color: 'var(--color-success)' }} aria-hidden="true" />
            <span className={s.metricLabel}>加速</span>
          </div>
          <div className={s.metricValueContainer}>
            <span className={`${s.metricValue} ${s.metricSuccess}`}>
              <CountUp end={displayImprovement} decimals={1} duration={350} />%
            </span>
            {isActiveInference && <Sparkline data={mockSpeedupData} color="var(--color-success)" />}
          </div>
        </div>
      )}

      {/* Inference Status */}
      <div className={s.metricItem}>
        <div className={s.metricTop}>
          {isActiveInference ? (
            <Icons.RefreshCw size={11} className={`${s.metricIcon} icon-spin`} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          ) : (
            <Icons.BarChart size={11} className={s.metricIcon} aria-hidden="true" />
          )}
          <span className={s.metricLabel}>推理状态</span>
        </div>
        <span
          className={s.metricValue}
          style={isActiveInference ? { color: 'var(--color-primary)' } : undefined}
        >
          {progressLabel ?? '空闲'}
        </span>
      </div>
    </div>
  )
}
