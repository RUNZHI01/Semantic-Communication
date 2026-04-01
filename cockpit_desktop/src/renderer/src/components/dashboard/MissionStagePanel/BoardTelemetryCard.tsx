import { Descriptions, Typography } from 'antd'
import { PanelCard } from '../../shared/PanelCard'
import { ToneTag } from '../../shared/ToneTag'
import { Icons } from '../../icons'
import { SkeletonCard } from '../../loading'
import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import s from './BoardTelemetryCard.module.css'

const { Text } = Typography

interface BoardTelemetryCardProps {
  system: UseQueryResult<SystemStatusResponse>
}

export function BoardTelemetryCard({ system }: BoardTelemetryCardProps) {
  const status = system.data
  const inf = status?.active_inference

  return (
    <PanelCard title="板卡遥测" icon={Icons.Cpu}>
      {system.isPending && <SkeletonCard lines={4} height={160} />}
      {system.isError && (
        <Text className={s.emptyText}>
          {system.error instanceof Error ? system.error.message : '加载失败'}
        </Text>
      )}
      {status && (
        <Descriptions column={1} size="small" styles={{ label: { color: 'var(--color-text-label)', width: 80 }, content: {} }}>
          <Descriptions.Item label="在线">
            <div className={s.metricItem} role="status" aria-live="polite">
              <span className={`status-dot ${status.live.board_online ? 'status-online' : 'status-offline'}`} aria-hidden="true" />
              <ToneTag tone={status.live.board_online ? 'success' : 'neutral'}>
                {status.live.board_online ? 'ONLINE' : 'OFFLINE'}
              </ToneTag>
            </div>
          </Descriptions.Item>
          <Descriptions.Item label="guard">
            <ToneTag tone="neutral">{status.live.guard_state}</ToneTag>
          </Descriptions.Item>
          <Descriptions.Item label="fault">
            <ToneTag tone={status.live.last_fault_code !== 'NONE' ? 'warning' : 'neutral'}>
              {status.live.last_fault_code}
            </ToneTag>
          </Descriptions.Item>
          <Descriptions.Item label="remoteproc">
            <span className="text-number font-mono metricValue">
              {String(status.live.remoteproc_state ?? '—')}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="rpmsg">
            <span className="text-number font-mono metricValue">
              {String(status.live.rpmsg_device ?? '—')}
            </span>
          </Descriptions.Item>
          <Descriptions.Item label="作业">
            <div className={s.metricItem} role="status" aria-live="polite">
              {inf?.running ? (
                <>
                  <span className="status-dot status-online status-pulse" aria-hidden="true" />
                  <ToneTag tone="info">RUNNING</ToneTag>
                </>
              ) : (
                <ToneTag tone="neutral">IDLE</ToneTag>
              )}
            </div>
            {inf?.message && (
              <Text className="text-caption" style={{ display: 'block', marginTop: 3 }}>
                {inf.message}
              </Text>
            )}
          </Descriptions.Item>
          {status.live.status_note && (
            <Descriptions.Item label="说明">
              <Text className="text-caption">{status.live.status_note}</Text>
            </Descriptions.Item>
          )}
        </Descriptions>
      )}
    </PanelCard>
  )
}
