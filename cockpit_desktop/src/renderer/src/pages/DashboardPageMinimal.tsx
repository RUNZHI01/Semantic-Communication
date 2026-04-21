import { memo, useMemo, useState, useEffect, useCallback, useRef } from 'react'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { useAircraftPosition } from '../hooks/useAircraftPosition'
import { useInferenceProgressPoll } from '../hooks/useInferenceProgress'
import { useBatchStatePoll } from '../hooks/useBatchState'
import { useAppStore } from '../stores/appStore'
import { useCryptoStatus } from '../hooks/useCryptoStatus'
import {
  useProbeBoard,
  useRunInferenceBatch,
  useRunMnnBatch,
  useRunBaseline,
  useSetBoardAccess,
} from '../hooks/useActions'
import { HeroMetrics } from '../components/dashboard/HeroMetrics'
import { MinimalStatusPanel } from '../components/dashboard/MinimalStatusPanel'
import { CryptoStatusPanel } from '../components/dashboard/CryptoStatusPanel'
import { FlightPanel } from '../components/dashboard/FlightPanel'
import { PageTransition, StaggeredList, AnimatedListItem } from '../components/animations'
import { Icons } from '../components/icons'
import { CountUp } from '../components/shared/CountUp'
import s from './DashboardPageMinimal.module.css'

const LIVE_LOG_ACTIONS = ['Processing block', 'Allocating memory', 'Optimizing tensor', 'Compiling kernel', 'Syncing device']

type AuthSigPolicy = 'DUAL_REQUIRED' | 'SM2_ONLY' | 'MLDSA_ONLY'

const AUTH_POLICY_OPTIONS: { value: AuthSigPolicy; label: string }[] = [
  { value: 'DUAL_REQUIRED', label: '双因子: SM2 + ML-DSA' },
  { value: 'SM2_ONLY', label: '仅 SM2' },
  { value: 'MLDSA_ONLY', label: '仅 ML-DSA' },
]

const AUTH_POLICY_HINTS: Record<AuthSigPolicy, string> = {
  DUAL_REQUIRED: '同时校验 SM2 与 ML-DSA 标识，最接近当前完整认证链路。',
  SM2_ONLY: '仅保留国密签名身份校验，便于单独验证 SM2 链路。',
  MLDSA_ONLY: '仅保留后量子签名身份校验，便于单独验证 ML-DSA 链路。',
}

function normalizeAuthSigPolicy(rawValue: string | undefined): AuthSigPolicy {
  const normalized = String(rawValue || '').trim().toUpperCase()
  if (normalized === 'SM2_ONLY' || normalized === 'MLDSA_ONLY') {
    return normalized
  }
  return 'DUAL_REQUIRED'
}

const LiveLogStream = memo(function LiveLogStream({ isRunning }: { isRunning: boolean }) {
  const [logs, setLogs] = useState<string[]>([])

  useEffect(() => {
    if (!isRunning) {
      setLogs([])
      return
    }

    const id = setInterval(() => {
      const now = new Date().toLocaleTimeString('en-US', { hour12: false })
      const action = LIVE_LOG_ACTIONS[Math.floor(Math.random() * LIVE_LOG_ACTIONS.length)]
      const blockId = Math.floor(Math.random() * 1000)
      setLogs((prev) => [...prev, `[${now}] ${action} ${blockId}... OK`].slice(-3))
    }, 800)

    return () => clearInterval(id)
  }, [isRunning])

  if (!isRunning || logs.length === 0) {
    return null
  }

  return (
    <div className={s.liveLogStream}>
      {logs.map((log, i) => (
        <div key={`${log}-${i}`} className={s.logEntry} style={{ opacity: 0.4 + (i * 0.3) }}>
          {log}
        </div>
      ))}
    </div>
  )
})

type GpsForwardStreamProps = {
  isActive: boolean
  sourceLabel?: string
  fixType?: string
  satellites?: number
  latitude?: number
  longitude?: number
  altitudeMeters?: number
}

const GpsForwardStream = memo(function GpsForwardStream({
  isActive,
  sourceLabel,
  fixType,
  satellites,
  latitude,
  longitude,
  altitudeMeters,
}: GpsForwardStreamProps) {
  const [gpsLogs, setGpsLogs] = useState<string[]>([])

  useEffect(() => {
    if (!isActive) {
      setGpsLogs([])
      return
    }

    const id = setInterval(() => {
      const now = new Date().toLocaleTimeString('en-US', { hour12: false })
      const lat = latitude ?? (30.5 + Math.random() * 0.01)
      const lon = longitude ?? (114.3 + Math.random() * 0.01)
      const alt = altitudeMeters ?? (500 + Math.random() * 10)
      const seq = Math.floor(Math.random() * 65535)
      setGpsLogs((prev) => {
        const nextLog = `[${now}] COORD_FWD seq=${seq} lat=${lat.toFixed(6)} lon=${lon.toFixed(6)} alt=${alt.toFixed(1)}m → RTOS OK`
        return [...prev, nextLog].slice(-5)
      })
    }, 600)

    return () => clearInterval(id)
  }, [isActive, latitude, longitude, altitudeMeters])

  if (!isActive) {
    return null
  }

  return (
    <div className={`${s.sectionCard} ${s.alertModeCard}`} style={{ marginTop: '12px' }}>
      <div className={s.alertModeHeader}>
        <Icons.Navigation size={20} style={{ color: 'var(--color-error)' }} />
        <div>
          <div className={s.alertModeTitle}>北斗定位持续下发中</div>
          <div className={s.alertModeSubtitle}>链路劣化，图像张量传输已挂起，仅向 RTOS 下发定位坐标</div>
        </div>
        <div className={s.progressBadge} style={{ marginLeft: 'auto' }}>
          <span className={s.pulseDot} style={{ background: 'var(--color-error)' }} />
          持续传输
        </div>
      </div>
      <div className={s.liveLogStream} style={{ marginTop: '8px' }}>
        {gpsLogs.length > 0 ? gpsLogs.map((log, i) => (
          <div key={`gps-${i}`} className={s.logEntry} style={{ opacity: 0.3 + (i * 0.15), color: 'var(--color-error)' }}>
            {log}
          </div>
        )) : (
          <div className={s.logEntry} style={{ color: 'var(--color-text-muted)' }}>等待坐标下发日志...</div>
        )}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px' }}>
        定位源: {sourceLabel ?? '—'} · 定位类型: {fixType ?? '—'} · 卫星: {satellites ?? '—'}
      </div>
    </div>
  )
})

export function DashboardPageMinimal() {
  const system = useSystemStatus()
  const aircraft = useAircraftPosition()
  const inferenceProgress = useInferenceProgressPoll()
  const batchState = useBatchStatePoll()

  const activeJobId = useAppStore((s) => s.activeJobId)
  const lastCompletedInference = useAppStore((s) => s.lastCompletedInference)
  const chinaTheater = useAppStore((s) => s.chinaTheater)
  const setChinaTheater = useAppStore((s) => s.setChinaTheater)
  const [boardPassword, setBoardPassword] = useState('')
  const [authEnabled, setAuthEnabled] = useState(false)
  const [authSigPolicy, setAuthSigPolicy] = useState<AuthSigPolicy>('DUAL_REQUIRED')
  const [authDirty, setAuthDirty] = useState(false)
  const [toasts, setToasts] = useState<{ id: number; text: string; type: 'success' | 'error' }[]>([])
  const toastIdRef = useRef(0)
  const batch = batchState.isError ? undefined : batchState.data

  const { data: cryptoData } = useCryptoStatus()
  const currentMode = cryptoData?.service_mode?.current_mode

  const probeMut = useProbeBoard()
  const batchMut = useRunInferenceBatch()
  const mnnBatchMut = useRunMnnBatch()
  const baselineMut = useRunBaseline()
  const boardAccessMut = useSetBoardAccess()

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    toastIdRef.current += 1
    const id = toastIdRef.current
    setToasts((prev) => [...prev, { id, text, type }])
    setTimeout(() => removeToast(id), 3000)
  }, [removeToast])

  useEffect(() => {
    if (authDirty) return
    setAuthEnabled(Boolean(cryptoData?.auth_enabled))
    setAuthSigPolicy(normalizeAuthSigPolicy(cryptoData?.sig_policy))
  }, [cryptoData?.auth_enabled, cryptoData?.sig_policy, authDirty])

  const handleRunInference = useMemo(
    () => () => {
      batchMut.mutate({ count: 300 }, {
        onSuccess: (data) => {
          if (data.status === 'already_running') {
            showToast('TVM 300 张任务已在运行中', 'success')
          } else if (data.status === 'started') {
            showToast('TVM 300 张任务已启动', 'success')
          } else {
            showToast(data.message || 'TVM 300 张任务启动失败', 'error')
          }
        },
        onError: (error) => {
          showToast(`启动失败: ${error.message}`, 'error')
        }
      })
    },
    [batchMut, showToast],
  )

  const handleRunMnnInference = useMemo(
    () => () => {
      mnnBatchMut.mutate({ count: 300 }, {
        onSuccess: (data) => {
          if (data.status === 'already_running') {
            showToast('MNN 300 张任务已在运行中', 'success')
          } else if (data.status === 'started') {
            showToast('MNN 300 张任务已启动', 'success')
          } else {
            showToast(data.message || 'MNN 300 张任务启动失败', 'error')
          }
        },
        onError: (error) => {
          showToast(`启动失败: ${error.message}`, 'error')
        },
      })
    },
    [mnnBatchMut, showToast],
  )

  const handleSavePassword = useMemo(
    () => () => {
      if (!boardPassword.trim()) {
        showToast('请输入板卡密码', 'error')
        return
      }
      boardAccessMut.mutate({ password: boardPassword }, {
        onSuccess: () => {
          showToast('密码已保存，现在可以启动推理了', 'success')
          setBoardPassword('')
        },
        onError: (error) => {
          showToast(`保存密码失败: ${error.message}`, 'error')
        }
      })
    },
    [boardPassword, boardAccessMut, showToast],
  )

  const handleSaveAuth = useMemo(
    () => () => {
      boardAccessMut.mutate(
        {
          auth_enabled: authEnabled,
          auth_sig_policy: authSigPolicy,
        },
        {
          onSuccess: () => {
            setAuthDirty(false)
            showToast(authEnabled ? `认证策略已保存: ${authSigPolicy}` : '认证面已关闭', 'success')
          },
          onError: (error) => {
            showToast(`保存认证设置失败: ${error.message}`, 'error')
          },
        },
      )
    },
    [authEnabled, authSigPolicy, boardAccessMut, showToast],
  )

  // Derived data
  const status = system.data
  const results = status?.recent_results
  const currentResultFromStatus = (
    results?.['current']?.execution_mode === 'live' && results?.['current']?.status === 'success'
      ? results?.['current']
      : undefined
  )
  const currentResultFromStore = (
    lastCompletedInference?.variant === 'current'
    && lastCompletedInference?.execution_mode === 'live'
    && lastCompletedInference?.status === 'success'
  ) ? lastCompletedInference : undefined
  const currentResult = currentResultFromStore ?? currentResultFromStatus
  const baselineResult = results?.['baseline']
  const payloadMs = currentResult?.timings?.payload_ms
  const baselineMs = baselineResult?.timings?.payload_ms
  const speedup = (payloadMs != null && baselineMs != null && baselineMs > 0)
    ? ((baselineMs - payloadMs) / baselineMs * 100)
    : null

  const batchServiceMode = batch?.service_mode as string | undefined
  const batchEngine = (batch?.engine === 'mnn' ? 'mnn' : 'tvm') as 'mnn' | 'tvm'
  const batchEngineLabel = batchEngine === 'mnn' ? 'MNN' : 'TVM'
  const totalImages = Math.max(1, batch?.total ?? 300)
  const progress = Math.max(0, Math.min(batch?.completed ?? 0, totalImages))
  const batchSuccess = Math.max(0, batch?.success ?? 0)
  const batchFallback = Math.max(0, batch?.fallback ?? 0)
  const isRunning = batch?.status === 'running'
  const isDone = batch?.status === 'done'
  const modeTag = batchServiceMode === 'ROI_ONLY' ? ' (降采样 3:1)' : ''
  const currentStage = isRunning
    ? batchEngine === 'mnn'
      ? (progress > 0 ? `MNN 动态尺寸批量 ${progress}/${totalImages}` : 'MNN 动态尺寸批量执行中')
      : `TVM 在线推进 ${progress}/${totalImages}${modeTag}`
    : isDone
      ? batchFallback > 0
        ? `批量结束：成功 ${batchSuccess}，回退 ${batchFallback}`
        : batchEngine === 'mnn'
          ? `MNN 批量完成：${progress}/${totalImages}`
          : `批量完成：${progress}/${totalImages}${modeTag}`
      : '等待操作员启动 TVM 300 张'
  const progressBadge = isRunning
    ? '运行中'
    : isDone
      ? batchFallback > 0
        ? (batchSuccess > 0 ? '部分回退' : '已回退')
        : '已完成'
      : '等待触发'
  const progressSubtitle = batchEngine === 'mnn'
    ? `${totalImages} 张 MNN 动态尺寸推理`
    : batchServiceMode === 'ROI_ONLY'
      ? `${totalImages} 张降采样推理 (原 300 张跳帧 3:1)`
      : `${totalImages} 张 TVM 图像在线推进`
  const progressSuffix = isRunning ? '处理中' : isDone ? '已完成' : '待启动'
  const boardOnline = status?.live?.board_online ?? false
  const authHint = authEnabled
    ? AUTH_POLICY_HINTS[authSigPolicy]
    : '当前只保留 ML-KEM + SM4，会跳过 ML-DSA / SM2 身份认证。'
  const authStatusLabel = cryptoData?.auth_enabled
    ? `已保存: ${normalizeAuthSigPolicy(cryptoData?.sig_policy)}`
    : '已保存: 未启用'

  return (
    <PageTransition className={s.root}>
      {/* Ambient Mesh Gradient Background */}
      <div className={s.meshBackground}>
        <div className={s.meshBlob1} />
        <div className={s.meshBlob2} />
        <div className={s.meshBlob3} />
      </div>

      {/* Toast Notification Container */}
      <div className={s.toastContainer}>
        {toasts.map((toast) => (
          <div key={toast.id} className={`${s.toast} ${toast.type === 'error' ? s.toastError : s.toastSuccess}`}>
            {toast.type === 'error' ? <Icons.AlertTriangle size={16} /> : <Icons.Check size={16} />}
            <span>{toast.text}</span>
          </div>
        ))}
      </div>

      {/* Metrics Bar */}
      <div className={s.metricsBar}>
        <HeroMetrics system={system} inferenceProgress={inferenceProgress} batchState={batchState} />
        {currentMode && currentMode !== 'FULL_FRAME' && (
          <div className={s.modeBadgeTop} style={{
            background: currentMode === 'ALERT_ONLY' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.1)',
            color: currentMode === 'ALERT_ONLY' ? 'var(--color-error)' : '#d97706',
            border: `1px solid ${currentMode === 'ALERT_ONLY' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
            padding: '4px 10px',
            borderRadius: '100px',
            fontSize: '12px',
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginLeft: 'auto'
          }}>
            <span className={s.pulseDot} style={{ background: 'currentColor' }} />
            {currentMode === 'ALERT_ONLY' ? '仅定位传输 (ALERT_ONLY)' : '降采样传输 (ROI_ONLY)'}
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className={s.mainContent}>
        {/* Left: Primary Panel (62%) */}
        <div className={s.leftPanel}>
          <StaggeredList staggerDelay={0.06}>
            <AnimatedListItem>
              {/* Progress Section */}
              {/* Unified progress card — works for all modes and engines */}
              <div className={`${s.sectionCard} ${isRunning ? `${s.cardActiveGlow} ${s.scanlineOverlay}` : ''}`}>
                <div className={s.progressHeader}>
                  <div>
                    <div className={s.progressLabel}>{batchEngineLabel} 推理进度</div>
                    <div className={s.progressSubTitle}>{progressSubtitle} {currentMode === 'ROI_ONLY' && batchEngine !== 'mnn' && '(降采样中)'}</div>
                  </div>
                  <div className={s.progressBadge}>
                    {isRunning && <span className={s.pulseDot} />}
                    {progressBadge}
                  </div>
                </div>

                <div className={s.progressCount}>
                  <strong>{progress}</strong>
                  <span>/ {totalImages} {progressSuffix}</span>
                </div>

                <div className={s.progressTrack}>
                  <div
                    className={s.progressFill}
                    style={{ width: `${(progress / totalImages) * 100}%` }}
                  />
                </div>

                <div className={s.progressMeta}>
                  当前阶段：{currentStage}
                </div>

                <LiveLogStream isRunning={isRunning} />
              </div>

              <GpsForwardStream
                isActive={currentMode === 'ALERT_ONLY'}
                sourceLabel={aircraft.data?.source_label}
                fixType={aircraft.data?.fix?.type}
                satellites={aircraft.data?.fix?.satellites}
                latitude={aircraft.data?.position?.latitude}
                longitude={aircraft.data?.position?.longitude}
                altitudeMeters={aircraft.data?.kinematics?.altitude_m}
              />
            </AnimatedListItem>

            <AnimatedListItem>
              {/* Action Section */}
              <div className={s.sectionCard}>
                <div className={s.sectionTitle}>执行操作</div>

                <button
                  className={s.btnFilled}
                  onClick={handleRunInference}
                  disabled={batchMut.isPending || mnnBatchMut.isPending || isRunning}
                >
                  {batchMut.isPending ? <span className={s.spinner} /> : <Icons.Play size={18} />}
                  <span>
                    {batchMut.isPending
                      ? '启动中...'
                      : currentMode === 'ROI_ONLY'
                        ? '启动 TVM 降采样扫描 (有效预估 100 帧)'
                        : '启动 TVM 推理 (300 张)'}
                  </span>
                </button>

                <div className={s.actionRow}>
                  <button
                    className={s.btnTonal}
                    onClick={() => probeMut.mutate()}
                    disabled={probeMut.isPending}
                  >
                    <span className={`${s.actionStatusDot} ${boardOnline ? s.statusDotOnline : s.statusDotOffline}`} />
                    {probeMut.isPending ? <span className={s.spinner} /> : <Icons.Radar size={16} />}
                    <span>探测板卡</span>
                  </button>

                  <button
                    className={s.btnTonal}
                    onClick={handleRunMnnInference}
                    disabled={mnnBatchMut.isPending || batchMut.isPending || isRunning}
                  >
                    {mnnBatchMut.isPending ? <span className={s.spinner} /> : <Icons.FileText size={16} />}
                    <span>MNN推理</span>
                  </button>

                  <button
                    className={s.btnTonal}
                    onClick={() => baselineMut.mutate({ imageIndex: 0 })}
                    disabled={baselineMut.isPending}
                  >
                    {baselineMut.isPending ? <span className={s.spinner} /> : <Icons.Activity size={16} />}
                    <span>PyTorch Live</span>
                  </button>
                </div>
              </div>
            </AnimatedListItem>

            <AnimatedListItem className={s.flex1Item}>
              {/* Result Comparison — uses flex:1 to fill remaining space */}
              <div className={`${s.resultCard} ${speedup != null && speedup > 0 ? s.cardSuccessGlow : ''}`} style={{ flex: 1 }}>
                <div className={s.sectionTitle}>推理结果对比</div>
                {payloadMs != null ? (
                  <>
                    <div className={s.comparisonShowcase}>
                      {baselineMs != null && (
                        <div className={s.barRow}>
                          <div className={s.barLabel}>PyTorch参考</div>
                          <div className={s.barTrack}>
                            <div className={s.barFillBaseline} style={{ width: '100%' }} />
                          </div>
                          <div className={s.barValue}>
                            <CountUp end={baselineMs} decimals={1} duration={400} /> ms
                          </div>
                        </div>
                      )}
                      <div className={s.barRow}>
                        <div className={s.barLabel}>TVM</div>
                        <div className={s.barTrack}>
                          <div
                            className={s.barFillCurrent}
                            style={{ width: `${Math.min((payloadMs / (baselineMs || payloadMs || 1)) * 100, 100)}%` }}
                          />
                        </div>
                        <div className={s.barValueHighlight}>
                          <span><CountUp end={payloadMs} decimals={1} duration={400} /> ms</span>
                          {speedup != null && (
                            <span className={s.trendBadge} style={{
                              background: speedup >= 0 ? 'var(--color-success-container)' : 'var(--color-error-container)',
                              color: speedup >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                            }}>
                              {speedup >= 0 ? '↓' : '↑'} <CountUp end={Math.abs(speedup)} decimals={1} duration={400} />%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    {currentResult?.quality && (
                      <div className={s.qualityMetrics}>
                        {currentResult.quality.psnr_db != null && (
                          <div className={s.qualityItem}>
                            <span className={s.qualityLabel}>PSNR</span>
                            <span className={s.qualityValue}>{currentResult.quality.psnr_db.toFixed(2)} dB</span>
                          </div>
                        )}
                        {currentResult.quality.ssim != null && (
                          <div className={s.qualityItem}>
                            <span className={s.qualityLabel}>SSIM</span>
                            <span className={s.qualityValue}>{currentResult.quality.ssim.toFixed(4)}</span>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <div className={s.resultEmpty}>
                    <div className={s.emptyIconWrapper}>
                      <Icons.Activity size={24} className={s.emptyIcon} />
                    </div>
                    <div className={s.emptyTitle}>
                      暂无推理结果
                    </div>
                    <div className={s.emptySubtitle}>
                      点击上方「启动 TVM 推理 (300 张)」开始在线推进
                    </div>
                    <div className={s.emptyDescription}>
                      推理完成后将展示 TVM vs PyTorch 参考延迟对比、加速比、PSNR/SSIM 质量指标
                    </div>
                  </div>
                )}
              </div>
            </AnimatedListItem>

            <AnimatedListItem>
              {/* Board Password */}
              <div className={s.sectionCard}>
                <div className={s.sectionTitle}>板卡连接设置</div>
                <div className={s.passwordRow}>
                  <input
                    type="password"
                    placeholder="输入板卡密码"
                    aria-label="板卡密码"
                    autoComplete="current-password"
                    value={boardPassword}
                    onChange={(e) => setBoardPassword(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') handleSavePassword() }}
                    className={s.passwordInput}
                  />
                  <button
                    className={s.btnFilledSm}
                    onClick={handleSavePassword}
                    disabled={boardAccessMut.isPending}
                  >
                    {boardAccessMut.isPending ? '保存中...' : '保存'}
                  </button>
                </div>
                <div className={s.settingGroup}>
                  <div className={s.settingRow}>
                    <div className={s.settingMeta}>
                      <div className={s.settingLabel}>认证面配置</div>
                      <div className={s.settingCaption}>控制当前 ML-KEM 信道是否叠加 ML-DSA / SM2 身份认证。</div>
                    </div>
                    <label className={s.authCheck}>
                      <input
                        type="checkbox"
                        checked={authEnabled}
                        onChange={(e) => {
                          setAuthEnabled(e.target.checked)
                          setAuthDirty(true)
                        }}
                      />
                      <span>启用认证</span>
                    </label>
                  </div>
                  <div className={s.settingStack}>
                    <label className={s.formLabel} htmlFor="auth-sig-policy">认证策略</label>
                    <select
                      id="auth-sig-policy"
                      className={s.selectInput}
                      value={authSigPolicy}
                      disabled={!authEnabled || boardAccessMut.isPending}
                      onChange={(e) => {
                        setAuthSigPolicy(normalizeAuthSigPolicy(e.target.value))
                        setAuthDirty(true)
                      }}
                    >
                      {AUTH_POLICY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className={s.settingCaption}>{authHint}</div>
                  <div className={s.settingStatus}>{authStatusLabel}</div>
                  <div className={s.settingActions}>
                    <button
                      className={s.btnFilledSm}
                      onClick={handleSaveAuth}
                      disabled={boardAccessMut.isPending}
                    >
                      {boardAccessMut.isPending ? '保存中...' : '保存认证设置'}
                    </button>
                  </div>
                </div>
              </div>
            </AnimatedListItem>
          </StaggeredList>
        </div>

        {/* Right: Secondary Panel (38%) */}
        <div className={s.rightPanel}>
          <div className={s.mapSection}>
            <FlightPanel
              aircraft={aircraft}
              chinaTheater={chinaTheater}
              setChinaTheater={setChinaTheater}
            />
          </div>

          <MinimalStatusPanel
            system={system}
            inferenceProgress={inferenceProgress?.data}
            activeJobId={activeJobId}
          />

          <CryptoStatusPanel />
        </div>
      </div>
    </PageTransition>
  )
}
