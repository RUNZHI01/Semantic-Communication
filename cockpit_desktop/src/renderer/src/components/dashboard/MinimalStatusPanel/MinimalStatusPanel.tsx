import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import { Icons } from '../../icons'
import s from './MinimalStatusPanel.module.css'

interface MinimalStatusPanelProps {
  system: UseQueryResult<SystemStatusResponse>
  inferenceProgress: any
  activeJobId: string | null
}

export function MinimalStatusPanel({ system }: MinimalStatusPanelProps) {
  const status = system.data
  const live = status?.live
  const sp = status?.safety_panel
  const boardOnline = live?.board_online ?? false

  return (
    <div className={s.container}>
      <div className={s.sectionTitle}>
        <Icons.Activity size={13} style={{ color: 'var(--color-primary)' }} />
        <span>System Details</span>
      </div>

      <div className={s.detailList}>
        <div className={s.detailRow}>
          <span className={s.detailLabel}>Connection</span>
          <span className={s.detailValue}>
            <span className={`${s.statusDot} ${boardOnline ? s.online : s.offline}`} />
            {boardOnline ? 'Online' : 'Offline'}
          </span>
        </div>

        <div className={s.detailRow}>
          <span className={s.detailLabel}>Guard State</span>
          <span className={s.detailValueAccent}>{live?.guard_state ?? '—'}</span>
        </div>

        <div className={s.detailRow}>
          <span className={s.detailLabel}>Last Fault</span>
          <span className={sp?.last_fault_code ? s.detailValueWarning : s.detailValue}>
            {sp?.last_fault_code ?? 'None'}
          </span>
        </div>

        <div className={s.detailRow}>
          <span className={s.detailLabel}>Target</span>
          <span className={s.detailValue}>{live?.target ?? '—'}</span>
        </div>
      </div>
    </div>
  )
}
