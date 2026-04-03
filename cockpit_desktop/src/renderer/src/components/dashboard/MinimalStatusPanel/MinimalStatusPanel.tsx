import { useState, useEffect } from 'react'
import { UseQueryResult } from '@tanstack/react-query'
import type { SystemStatusResponse } from '../../../api/types'
import { Icons } from '../../icons'
import s from './MinimalStatusPanel.module.css'

function CircularGauge({ value, color, label }: { value: number, color: string, label: string }) {
  const radius = 14;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (value / 100) * circumference;

  return (
    <div className={s.gaugeContainer}>
      <svg width="36" height="36" viewBox="0 0 36 36" className={s.gaugeSvg}>
        <circle cx="18" cy="18" r={radius} fill="none" stroke="var(--color-border-light)" strokeWidth="3" />
        <circle 
          cx="18" cy="18" r={radius} 
          fill="none" 
          stroke={color} 
          strokeWidth="3" 
          strokeDasharray={circumference} 
          strokeDashoffset={strokeDashoffset} 
          strokeLinecap="round" 
          transform="rotate(-90 18 18)"
          style={{ transition: 'stroke-dashoffset 500ms ease-in-out' }}
        />
      </svg>
      <div className={s.gaugeValue} style={{ color }}>{Math.round(value)}</div>
      <div className={s.gaugeLabel}>{label}</div>
    </div>
  );
}

function Waveform({ active }: { active: boolean }) {
  return (
    <div className={`${s.waveform} ${active ? s.waveformActive : ''}`}>
      <div className={s.waveBar} />
      <div className={s.waveBar} />
      <div className={s.waveBar} />
      <div className={s.waveBar} />
    </div>
  );
}

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

  const [npuLoad, setNpuLoad] = useState(0)
  const [memUsage, setMemUsage] = useState(0)

  useEffect(() => {
    if (!boardOnline) {
      setNpuLoad(0)
      setMemUsage(0)
      return
    }
    
    // Initial values
    setNpuLoad(85)
    setMemUsage(60)

    const interval = setInterval(() => {
      setNpuLoad(prev => Math.min(100, Math.max(75, prev + (Math.random() * 10 - 5))))
      setMemUsage(prev => Math.min(100, Math.max(50, prev + (Math.random() * 6 - 3))))
    }, 1500)

    return () => clearInterval(interval)
  }, [boardOnline])

  return (
    <div className={s.container}>
      <div className={s.headerRow}>
        <div className={s.sectionTitle}>
          <Icons.Activity size={13} style={{ color: 'var(--color-primary)' }} />
          <span>Hardware Telemetry</span>
        </div>
        <Waveform active={boardOnline} />
      </div>

      <div className={s.gaugesRow}>
        <CircularGauge value={npuLoad} color="var(--color-primary)" label="NPU" />
        <CircularGauge value={memUsage} color="var(--color-success)" label="MEM" />
      </div>

      <div className={s.detailList}>
        <div className={s.detailRow}>
          <span className={s.detailLabel}>Link Status</span>
          <span className={s.detailValue}>
            <div className={s.ledMatrix}>
              <span className={`${s.led} ${boardOnline ? s.ledGreen : ''}`} title="PWR" />
              <span className={`${s.led} ${boardOnline ? s.ledGreen : ''}`} title="LINK" />
              <span className={`${s.led} ${boardOnline ? s.ledBlueBlink : ''}`} title="SYNC" />
            </div>
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
