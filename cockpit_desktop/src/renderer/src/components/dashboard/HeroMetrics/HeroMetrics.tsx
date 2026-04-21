import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import type { BatchStateResponse } from '../../../api/types/crypto'
import { Icons } from '../../icons'
import { CountUp } from '../../shared/CountUp'
import { useAppStore } from '../../../stores/appStore'
import s from './HeroMetrics.module.css'

function Sparkline({ data, color }: { data: number[], color: string }) {
  if (!data || data.length === 0) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 48;
  const height = 16;

  if (data.length === 1) {
    return (
      <svg width={width} height={height} className={s.sparkline} viewBox={`0 -2 ${width} ${height + 4}`}>
        <circle cx={width / 2} cy={height / 2} r={2.5} fill={color} />
      </svg>
    );
  }
  
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
  batchState?: UseQueryResult<BatchStateResponse>
}

export function HeroMetrics({ system, inferenceProgress, batchState }: HeroMetricsProps) {
  const status = system.data
  const results = status?.recent_results
  const lastCompletedInference = useAppStore((s) => s.lastCompletedInference)
  const currentFromStatus = results?.['current']
  const current = (
    lastCompletedInference?.variant === 'current'
    && lastCompletedInference?.execution_mode === 'live'
    && lastCompletedInference?.status === 'success'
  ) ? lastCompletedInference : currentFromStatus
  const baseline = results?.['baseline']
  const live = status?.live
  const boardOnline = live?.board_online ?? false

  const basePayloadCurrent = current?.timings?.payload_ms
  const payloadBaseline = baseline?.timings?.payload_ms
  const baseImprovementPct = (basePayloadCurrent && payloadBaseline && payloadBaseline > 0)
    ? ((payloadBaseline - basePayloadCurrent) / payloadBaseline * 100)
    : null

  const lp = inferenceProgress?.data?.live_progress
  const batch = batchState?.data
  const isSingleInferenceActive = !!inferenceProgress?.data && inferenceProgress.data.request_state === 'running'
  const isBatchActive = batch?.status === 'running'
  const isActiveInference = isSingleInferenceActive || isBatchActive
  const batchEngineLabel = batch?.engine === 'mnn' ? 'MNN 推理' : 'TVM 推理'
  const progressLabel = isSingleInferenceActive
    ? (lp?.label ?? inferenceProgress?.data?.status_category ?? inferenceProgress?.data?.request_state)
    : isBatchActive
      ? `${batchEngineLabel} ${batch?.completed ?? 0}/${batch?.total ?? 300}`
      : batch?.status === 'done'
        ? batch.fallback && batch.fallback > 0
          ? `批量结束 ${batch.success ?? 0}/${batch.total ?? 300} 成功`
          : '批量完成'
        : '空闲'

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
          {basePayloadCurrent != null ? (
            <>
              <span className={`${s.metricValue} ${s.metricHighlight}`}>
                <CountUp end={basePayloadCurrent} decimals={1} duration={350} /> ms
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
      {baseImprovementPct != null && (
        <div className={s.metricItem}>
          <div className={s.metricTop}>
            <Icons.TrendingUp size={11} className={s.metricIcon} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
            <span className={s.metricLabel}>加速</span>
          </div>
          <div className={s.metricValueContainer}>
            <span className={s.metricValueGiant}>
              <CountUp end={baseImprovementPct} decimals={1} duration={350} />%
            </span>
            {isActiveInference && <Sparkline data={mockSpeedupData} color="var(--color-primary)" />}
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
