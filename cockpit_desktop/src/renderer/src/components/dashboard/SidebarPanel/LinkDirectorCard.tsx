import { Space, Typography, Button } from 'antd'
import { PanelCard } from '../../shared/PanelCard'
import { ToneTag } from '../../shared/ToneTag'
import { Icons } from '../../icons'
import { SkeletonCard } from '../../loading'
import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import s from './LinkDirectorCard.module.css'

const { Text, Paragraph } = Typography

interface LinkDirectorCardProps {
  system: UseQueryResult<SystemStatusResponse>
  onSwitchProfile: (profileId: string) => void
  switchPending: boolean
}

export function LinkDirectorCard({ system, onSwitchProfile, switchPending }: LinkDirectorCardProps) {
  const status = system.data
  const ld = status?.link_director
  const profiles = ld?.profiles ?? []

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
            <ToneTag tone={ld.tone} label={ld.label ?? ld.selected_profile_label} />
            <span className={`text-number font-mono text-label ${s.profileId}`}>
              {ld.selected_profile_id ?? '—'}
            </span>
          </Space>
          {profiles.length > 0 && (
            <Space wrap size={4}>
              {profiles.map((p: any) => (
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
          )}
          {ld.summary && (
            <Paragraph className={s.summaryText}>
              {ld.summary}
            </Paragraph>
          )}
        </>
      )}
    </PanelCard>
  )
}
