import React from 'react'
import { Progress as AntProgress } from 'antd'
import { T } from '../../theme/tokens'

export interface CockpitProgressProps {
  percent?: number
  variant?: 'primary' | 'success' | 'warning' | 'danger'
  showAnimation?: boolean
  style?: React.CSSProperties
}

const VARIANT_COLORS: Record<string, { from: string; to: string }> = {
  primary: { from: T.accentBlue, to: T.accentCyan },
  success: { from: T.toneSuccess, to: T.accentTeal },
  warning: { from: T.toneWarning, to: T.toneError },
  danger:  { from: T.toneError, to: T.toneError },
}

export const CockpitProgress: React.FC<CockpitProgressProps> = ({
  percent,
  variant = 'primary',
  showAnimation = true,
  style,
}) => {
  const colors = VARIANT_COLORS[variant] ?? VARIANT_COLORS.primary

  return (
    <AntProgress
      percent={percent}
      strokeColor={{ '0%': colors.from, '100%': colors.to }}
      trailColor={T.bgSection}
      strokeWidth={4}
      showInfo={false}
      strokeLinecap="round"
      className={showAnimation ? 'progress-animated' : undefined}
      style={style}
    />
  )
}
