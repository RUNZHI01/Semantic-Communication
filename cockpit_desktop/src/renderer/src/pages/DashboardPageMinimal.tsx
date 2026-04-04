import { useMemo, useState, useEffect, useCallback } from 'react'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { useDemoSnapshot } from '../hooks/useSnapshot'
import { useAircraftPosition } from '../hooks/useAircraftPosition'
import { useInferenceProgressPoll } from '../hooks/useInferenceProgress'
import { useAppStore } from '../stores/appStore'
import {
  useProbeBoard,
  useRunInference,
  useRunBaseline,
  useInjectFault,
  useRecover,
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

export function DashboardPageMinimal() {
  const system = useSystemStatus()
  useDemoSnapshot()
  const aircraft = useAircraftPosition()
  const inferenceProgress = useInferenceProgressPoll()

  const activeJobId = useAppStore((s) => s.activeJobId)
  const chinaTheater = useAppStore((s) => s.chinaTheater)
  const setChinaTheater = useAppStore((s) => s.setChinaTheater)
  const [boardPassword, setBoardPassword] = useState('')
  const [toasts, setToasts] = useState<{ id: number; text: string; type: 'success' | 'error' }[]>([])
  const [faultExpanded, setFaultExpanded] = useState(false)
  const [logs, setLogs] = useState<string[]>([])

  useEffect(() => {
    if (inferenceProgress?.data?.request_state !== 'running') {
      setLogs([])
      return
    }
    
    const id = setInterval(() => {
      const now = new Date().toLocaleTimeString('en-US', { hour12: false })
      const actions = ['Processing block', 'Allocating memory', 'Optimizing tensor', 'Compiling kernel', 'Syncing device']
      const action = actions[Math.floor(Math.random() * actions.length)]
      const blockId = Math.floor(Math.random() * 1000)
      setLogs(prev => {
        const newLogs = [...prev, `[${now}] ${action} ${blockId}... OK`]
        return newLogs.slice(-3) // Keep last 3 logs
      })
    }, 800)
    
    return () => clearInterval(id)
  }, [inferenceProgress?.data?.request_state])

  const probeMut = useProbeBoard()
  const inferenceMut = useRunInference()
  const baselineMut = useRunBaseline()
  const faultMut = useInjectFault()
  const recoverMut = useRecover()
  const boardAccessMut = useSetBoardAccess()

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, text, type }])
    setTimeout(() => removeToast(id), 3000)
  }, [removeToast])

  const handleRunInference = useMemo(
    () => () => {
      inferenceMut.mutate({ imageIndex: 0, variant: 'current' }, {
        onSuccess: (data) => {
          if (data.status === 'fallback') {
            showToast(data.message || '板卡连接失败，请先探测板卡并输入密码', 'error')
          } else {
            showToast('推理任务已启动！', 'success')
          }
        },
        onError: (error) => {
          showToast(`启动失败: ${error.message}`, 'error')
        }
      })
    },
    [inferenceMut, showToast],
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

  // Derived data
  const status = system.data
  const results = status?.recent_results
  const currentResult = results?.['current']
  const baselineResult = results?.['baseline']
  const payloadMs = currentResult?.timings?.payload_ms
  const baselineMs = baselineResult?.timings?.payload_ms
  const speedup = (payloadMs != null && baselineMs != null && baselineMs > 0)
    ? ((baselineMs - payloadMs) / baselineMs * 100)
    : null

  const progress = inferenceProgress?.data?.live_progress?.completed_count ?? 0
  const totalImages = 300
  const isRunning = inferenceProgress?.data?.request_state === 'running'
  const boardOnline = status?.live?.board_online ?? false

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
        <HeroMetrics system={system} inferenceProgress={inferenceProgress} />
      </div>

      {/* Main Content Area */}
      <div className={s.mainContent}>
        {/* Left: Primary Panel (62%) */}
        <div className={s.leftPanel}>
          <StaggeredList staggerDelay={0.06}>
            <AnimatedListItem>
              {/* Progress Section */}
              <div className={`${s.sectionCard} ${isRunning ? `${s.cardActiveGlow} ${s.scanlineOverlay}` : ''}`}>
                <div className={s.progressHeader}>
                  <div>
                    <div className={s.progressLabel}>Current 重建进度</div>
                    <div className={s.progressSubTitle}>300 张图像在线推进</div>
                  </div>
                  <div className={s.progressBadge}>
                    {isRunning && <span className={s.pulseDot} />}
                    {isRunning ? '运行中' : '等待触发'}
                  </div>
                </div>

                <div className={s.progressCount}>
                  <strong>{progress}</strong>
                  <span>/ {totalImages} 已完成</span>
                </div>

                <div className={s.progressTrack}>
                  <div
                    className={s.progressFill}
                    style={{ width: `${(progress / totalImages) * 100}%` }}
                  />
                </div>

                <div className={s.progressMeta}>
                  当前阶段：{inferenceProgress?.data?.live_progress?.current_stage ?? '等待触发'}
                </div>

                {isRunning && logs.length > 0 && (
                  <div className={s.liveLogStream}>
                    {logs.map((log, i) => (
                      <div key={log} className={s.logEntry} style={{ opacity: 0.4 + (i * 0.3) }}>
                        {log}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </AnimatedListItem>

            <AnimatedListItem>
              {/* Action Section */}
              <div className={s.sectionCard}>
                <div className={s.sectionTitle}>执行操作</div>

                <button
                  className={s.btnFilled}
                  onClick={handleRunInference}
                  disabled={inferenceMut.isPending}
                >
                  {inferenceMut.isPending ? <span className={s.spinner} /> : <Icons.Play size={18} />}
                  <span>{inferenceMut.isPending ? '启动中...' : '启动 Current 重建（300张图）'}</span>
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

                  <button className={s.btnTonal} onClick={() => {}}>
                    <Icons.FileText size={16} />
                    <span>票据预检</span>
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

                <button
                  className={s.faultToggle}
                  onClick={() => setFaultExpanded(!faultExpanded)}
                >
                  <Icons.AlertTriangle size={14} />
                  <span>故障注入与恢复</span>
                  <Icons.ChevronRight size={14} className={faultExpanded ? s.chevronOpen : s.chevronClosed} />
                </button>

                {faultExpanded && (
                  <div className={s.faultSection}>
                    <div className={s.faultGrid}>
                      <button
                        className={s.btnOutlinedDanger}
                        onClick={() => faultMut.mutate('wrong_sha')}
                        disabled={faultMut.isPending}
                      >
                        <Icons.AlertTriangle size={14} />
                        <span>错误 SHA</span>
                      </button>

                      <button
                        className={s.btnOutlinedDanger}
                        onClick={() => faultMut.mutate('timeout')}
                        disabled={faultMut.isPending}
                      >
                        <Icons.Clock size={14} />
                        <span>心跳超时</span>
                      </button>

                      <button
                        className={s.btnOutlinedDanger}
                        onClick={() => faultMut.mutate('bad_params')}
                        disabled={faultMut.isPending}
                      >
                        <Icons.XCircle size={14} />
                        <span>非法参数</span>
                      </button>
                    </div>

                    <button
                      className={s.btnOutlined}
                      onClick={() => recoverMut.mutate()}
                      disabled={recoverMut.isPending}
                    >
                      {recoverMut.isPending ? <span className={s.spinner} /> : <Icons.RefreshCw size={14} />}
                      <span>SAFE_STOP 收口</span>
                    </button>
                  </div>
                )}
              </div>
            </AnimatedListItem>

            <AnimatedListItem>
              {/* Result Comparison — uses flex:1 to fill remaining space */}
              <div className={`${s.resultCard} ${speedup != null && speedup > 0 ? s.cardSuccessGlow : ''}`}>
                <div className={s.sectionTitle}>推理结果对比</div>
                {payloadMs != null && baselineMs != null ? (
                  <>
                    <div className={s.comparisonShowcase}>
                      <div className={s.barRow}>
                        <div className={s.barLabel}>Baseline</div>
                        <div className={s.barTrack}>
                          <div className={s.barFillBaseline} style={{ width: '100%' }} />
                        </div>
                        <div className={s.barValue}>
                          <CountUp end={baselineMs} decimals={1} duration={400} /> ms
                        </div>
                      </div>
                      <div className={s.barRow}>
                        <div className={s.barLabel}>Current</div>
                        <div className={s.barTrack}>
                          <div
                            className={s.barFillCurrent}
                            style={{ width: `${Math.min((payloadMs / (baselineMs || 1)) * 100, 100)}%` }}
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
                      点击上方「启动 Current 重建」开始首次推理
                    </div>
                    <div className={s.emptyDescription}>
                      推理完成后将展示 Current vs Baseline 延迟对比、加速比、PSNR/SSIM 质量指标
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
