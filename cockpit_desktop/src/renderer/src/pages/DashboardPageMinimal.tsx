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
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [faultExpanded, setFaultExpanded] = useState(false)

  const probeMut = useProbeBoard()
  const inferenceMut = useRunInference()
  const baselineMut = useRunBaseline()
  const faultMut = useInjectFault()
  const recoverMut = useRecover()
  const boardAccessMut = useSetBoardAccess()

  const showToast = useCallback((text: string, type: 'success' | 'error') => {
    setToastMessage({ text, type })
  }, [])

  useEffect(() => {
    if (!toastMessage) return
    const id = setTimeout(() => setToastMessage(null), 3000)
    return () => clearTimeout(id)
  }, [toastMessage])

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

  return (
    <PageTransition className={s.root}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`${s.toast} ${toastMessage.type === 'error' ? s.toastError : s.toastSuccess}`}>
          {toastMessage.type === 'error' ? <Icons.AlertTriangle size={16} /> : <Icons.Check size={16} />}
          <span>{toastMessage.text}</span>
        </div>
      )}

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
              <div className={s.sectionCard}>
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
              <div className={s.resultCard}>
                <div className={s.sectionTitle}>推理结果对比</div>
                {payloadMs != null && baselineMs != null ? (
                  <>
                    <div className={s.resultRow}>
                      <div className={s.resultItem}>
                        <span className={s.resultLabel}>Current</span>
                        <span className={s.resultValueHighlight}>
                          <CountUp end={payloadMs} decimals={1} duration={400} /> ms
                        </span>
                      </div>
                      <div className={s.resultDivider} />
                      <div className={s.resultItem}>
                        <span className={s.resultLabel}>Baseline</span>
                        <span className={s.resultValue}>
                          <CountUp end={baselineMs} decimals={1} duration={400} /> ms
                        </span>
                      </div>
                    </div>
                    {speedup != null && (
                      <div className={s.speedupBar}>
                        <div className={s.speedupLabel}>加速比</div>
                        <div className={s.speedupValue}>
                          <CountUp end={speedup} decimals={1} duration={400} />% faster
                        </div>
                      </div>
                    )}
                    {currentResult?.quality && (
                      <div className={s.qualityRow}>
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
                    <Icons.Zap size={32} style={{ opacity: 0.25, marginBottom: 12 }} />
                    <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--color-text-secondary)', marginBottom: 4 }}>
                      暂无推理结果
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--color-text-tertiary)' }}>
                      点击上方「启动 Current 重建」开始首次推理
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 8 }}>
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
        </div>
      </div>
    </PageTransition>
  )
}
