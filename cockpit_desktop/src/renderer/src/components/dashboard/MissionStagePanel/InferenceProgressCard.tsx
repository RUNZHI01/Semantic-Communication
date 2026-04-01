import { Space, Typography } from 'antd'
import { PanelCard } from '../../shared/PanelCard'
import { ToneTag } from '../../shared/ToneTag'
import { InferenceTimeline } from '../../charts/InferenceTimeline'
import { CockpitProgress } from '../../ios/CockpitProgress'
import { Icons } from '../../icons'
import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse, RunInferenceResponse } from '../../../api/types'
import s from './InferenceProgressCard.module.css'

const { Text } = Typography

interface InferenceProgressCardProps {
  activeJobId: string | null
  inferenceProgress: UseQueryResult<RunInferenceResponse | null>
  system: UseQueryResult<SystemStatusResponse>
}

export function InferenceProgressCard({ activeJobId, inferenceProgress, system }: InferenceProgressCardProps) {
  const status = system.data

  return (
    <PanelCard title="推理进度" icon={Icons.Timer} variant="highlight">
      {!activeJobId && <Text className={s.emptyText}>无活跃推理任务</Text>}
      {activeJobId && (
        <>
          {inferenceProgress.isPending && <Text className={s.loadingText}>查询进度...</Text>}
          {inferenceProgress.isError && <ToneTag tone="error">查询失败</ToneTag>}
          {inferenceProgress.data &&
            (() => {
              const d = inferenceProgress.data
              const lp = d.live_progress
              return (
                <Space direction="vertical" className={s.container} size={4}>
                  <Space wrap size={4}>
                    <ToneTag tone="info" className={`${s.jobTag} text-number font-mono`}>job: {d.job_id ?? activeJobId}</ToneTag>
                    <ToneTag
                      tone={lp?.tone}
                      label={lp?.label ?? d.status_category ?? d.request_state}
                    />
                  </Space>
                  {lp?.percent != null && (
                    <CockpitProgress
                      percent={Math.round(lp.percent)}
                      variant={d.request_state === 'running' ? 'primary' : 'success'}
                      showAnimation
                    />
                  )}
                  {lp?.current_stage && (
                    <div className={s.stageRow}>
                      <Icons.Clock size={12} className={s.stageIcon} />
                      <Text className={s.stageText}>
                        {lp.current_stage}
                      </Text>
                    </div>
                  )}
                  {d.message && <Text className={s.messageText}>{d.message}</Text>}
                </Space>
              )
            })()}
          {status?.recent_results && Object.keys(status.recent_results).length > 0 && (
            <div className={s.timelineWrapper}>
              <InferenceTimeline results={status.recent_results as Record<string, any>} />
            </div>
          )}
        </>
      )}
    </PanelCard>
  )
}
