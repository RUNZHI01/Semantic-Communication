import { useMemo, useState, useEffect, useCallback } from 'react'
import { useSystemStatus } from '../hooks/useSystemStatus'
import { useDemoSnapshot } from '../hooks/useSnapshot'
import { useAircraftPosition } from '../hooks/useAircraftPosition'
import { useInferenceProgressPoll } from '../hooks/useInferenceProgress'
import { useBatchStatePoll } from '../hooks/useBatchState'
import { useAppStore } from '../stores/appStore'
import {
  useProbeBoard,
  useRunInferenceBatch,
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
  const batchState = useBatchStatePoll()

  const activeJobId = useAppStore((s) => s.activeJobId)
  const chinaTheater = useAppStore((s) => s.chinaTheater)
  const setChinaTheater = useAppStore((s) => s.setChinaTheater)
  const [boardPassword, setBoardPassword] = useState('')
  const [toasts, setToasts] = useState<{ id: number; text: string; type: 'success' | 'error' }[]>([])
  const [faultExpanded, setFaultExpanded] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const batch = batchState.isError ? undefined : batchState.data

  useEffect(() => {
    if (batch?.status !== 'running') {
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
  }, [batch?.status])

  const probeMut = useProbeBoard()
  const batchMut = useRunInferenceBatch()
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
      batchMut.mutate({ count: 300 }, {
        onSuccess: (data) => {
          if (data.status === 'already_running') {
            showToast('Current 300 张任务已在运行中', 'success')
          } else if (data.status === 'started') {
            showToast('Current 300 张任务已启动', 'success')
          } else {
            showToast(data.message || 'Current 300 张任务启动失败', 'error')
          }
        },
        onError: (error) => {
          showToast(`启动失败: ${error.message}`, 'error')
        }
      })
    },
    [batchMut, showToast],
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
  const currentResult = (
    results?.['current']?.execution_mode === 'live' && results?.['current']?.status === 'success'
      ? results?.['current']
      : undefined
  )
  const baselineResult = results?.['baseline']
  const payloadMs = currentResult?.timings?.payload_ms
  const baselineMs = baselineResult?.timings?.payload_ms
  const speedup = (payloadMs != null && baselineMs != null && baselineMs > 0)
    ? ((baselineMs - payloadMs) / baselineMs * 100)
    : null

  const totalImages = Math.max(1, batch?.total ?? 300)
  const progress = Math.max(0, Math.min(batch?.completed ?? 0, totalImages))
  const batchSuccess = Math.max(0, batch?.success ?? 0)
  const batchFallback = Math.max(0, batch?.fallback ?? 0)
  const isRunning = batch?.status === 'running'
  const isDone = batch?.status === 'done'
  const currentStage = isRunning
    ? `Current 在线推进 ${progress}/${totalImages}`
    : isDone
      ? batchFallback > 0
        ? `批量结束：成功 ${batchSuccess}，回退 ${batchFallback}`
        : `批量完成：${progress}/${totalImages}`
      : '等待操作员启动 Current 300 张'
  const progressBadge = isRunning
    ? '运行中'
    : isDone
      ? batchFallback > 0
        ? (batchSuccess > 0 ? '部分回退' : '已回退')
        : '已完成'
      : '等待触发'
  const progressSubtitle = `${totalImages} 张图像在线推进`
  const progressSuffix = isRunning ? '处理中' : isDone ? '已完成' : '待启动'
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
        <HeroMetrics system={system} inferenceProgress={inferenceProgress} batchState={batchState} />
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
                    <div className={s.progressSubTitle}>{progressSubtitle}</div>
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
                  disabled={batchMut.isPending || isRunning}
                >
                  {batchMut.isPending ? <span className={s.spinner} /> : <Icons.Play size={18} />}
                  <span>{batchMut.isPending ? '启动中...' : '启动 Current 300 张重建'}</span>
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
                {payloadMs != null ? (
                  <>
                    <div className={s.comparisonShowcase}>
                      {baselineMs != null && (
                        <div className={s.barRow}>
                          <div className={s.barLabel}>Baseline</div>
                          <div className={s.barTrack}>
                            <div className={s.barFillBaseline} style={{ width: '100%' }} />
                          </div>
                          <div className={s.barValue}>
                            <CountUp end={baselineMs} decimals={1} duration={400} /> ms
                          </div>
                        </div>
                      )}
                      <div className={s.barRow}>
                        <div className={s.barLabel}>Current</div>
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
                      点击上方「启动 Current 300 张重建」开始在线推进
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
