import { Space, Typography, Button } from 'antd'
import { PanelCard } from '../../shared/PanelCard'
import { ToneTag } from '../../shared/ToneTag'
import { Icons } from '../../icons'
import { SkeletonCard } from '../../loading'
import { UseQueryResult } from '@tanstack/react-query'
import type { LinkDirectorProfile, SystemStatusResponse } from '../../../api/types'
import s from './LinkDirectorCard.module.css'

const { Text, Paragraph } = Typography

interface LinkDirectorCardProps {
  system: UseQueryResult<SystemStatusResponse>
  onSelectTransport: (mode: string) => void
  transportPending: boolean
  onSwitchProfile: (profileId: string) => void
  switchPending: boolean
}

const TRANSPORT_OPTIONS = [
  { mode: 'tcp', label: 'Tailscale / TCP' },
  { mode: 'usrp', label: 'USRP OTA' },
] as const

export function LinkDirectorCard({
  system,
  onSelectTransport,
  transportPending,
  onSwitchProfile,
  switchPending,
}: LinkDirectorCardProps) {
  const status = system.data
  const boardAccess = status?.board_access
  const ld = status?.link_director
  const profiles = (ld?.profiles ?? []) as LinkDirectorProfile[]
  const activeTransport = String(boardAccess?.transport_mode ?? 'tcp')
  const transportLabel = boardAccess?.transport_label ?? 'Tailscale / TCP'
  const transportTone = boardAccess?.transport_tone ?? 'info'
  const transportSummary = boardAccess?.transport_summary ?? '当前尚未读取到有效信道信息。'

  return (
    <PanelCard title="链路导演" icon={Icons.Network}>
      {system.isPending && <SkeletonCard lines={3} height={100} />}
      {system.isError && (
        <Text className={s.emptyText}>
          {system.error instanceof Error ? system.error.message : '加载失败'}
        </Text>
      )}
      {ld && (
        <>
          <Space wrap size={4} className={s.tagGroup}>
            <ToneTag tone={transportTone} label={transportLabel} />
            <ToneTag tone={ld.tone} label={ld.label ?? ld.selected_profile_label} />
            <span className={`text-number font-mono text-label ${s.profileId}`}>
              {ld.selected_profile_id ?? '—'}
            </span>
          </Space>

          <div className={s.section}>
            <Text className={s.sectionLabel}>数据面信道</Text>
            <Space wrap size={6}>
              {TRANSPORT_OPTIONS.map((option) => (
                <Button
                  key={option.mode}
                  size="small"
                  type={activeTransport === option.mode ? 'primary' : 'default'}
                  loading={transportPending && activeTransport !== option.mode}
                  onClick={() => onSelectTransport(option.mode)}
                  className="text-sm"
                >
                  {option.label}
                </Button>
              ))}
            </Space>
            <Paragraph className={s.summaryText}>{transportSummary}</Paragraph>
          </div>

          {profiles.length > 0 && (
            <div className={s.section}>
              <Text className={s.sectionLabel}>弱网预案</Text>
              <Space wrap size={6}>
                {profiles.map((p) => (
                  <Button
                    key={p.profile_id}
                    size="small"
                    type={p.active ? 'primary' : 'default'}
                    loading={switchPending && !p.active}
                    onClick={() => onSwitchProfile(p.profile_id)}
                    className="text-sm"
                  >
                    {p.label}
                  </Button>
                ))}
              </Space>
            </div>
          )}
          {ld.summary && (
            <Paragraph className={s.summaryText}>{ld.summary}</Paragraph>
          )}
        </>
      )}
    </PanelCard>
  )
}
