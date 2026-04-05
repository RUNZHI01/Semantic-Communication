import { useCryptoStatus } from '../../../hooks/useCryptoStatus'
import { postCryptoToggle, postCryptoTest } from '../../../api/client'
import s from './CryptoStatusPanel.module.css'
import { useState } from 'react'

const STATE_LABEL: Record<string, { label: string; tone: string }> = {
  idle: { label: '空闲', tone: 'neutral' },
  handshaking: { label: '握手中', tone: 'warn' },
  ready: { label: '已建立', tone: 'ok' },
  closed: { label: '已关闭', tone: 'off' },
  disabled: { label: '未启用', tone: 'off' },
}

export function CryptoStatusPanel() {
  const { data, isLoading, isError, refetch } = useCryptoStatus()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const enabled = data?.enabled ?? false
  const boardConfigured = data?.board_configured ?? false

  async function handleToggle() {
    try {
      await postCryptoToggle(!enabled)
      refetch()
    } catch { /* ignore */ }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      const r = await postCryptoTest()
      if (r.status === 'ok') {
        setTestResult({
          ok: true,
          msg: `握手 ${r.handshake_ms?.toFixed(1) ?? '?'}ms | 总耗时 ${r.wall_ms?.toFixed(0) ?? '?'}ms`,
        })
      } else {
        setTestResult({ ok: false, msg: r.message ?? 'unknown error' })
      }
      refetch()
    } catch (e) {
      setTestResult({ ok: false, msg: String(e) })
    } finally {
      setTesting(false)
    }
  }

  // 1) Board not configured — show prompt
  if (!boardConfigured && !enabled) {
    return (
      <div className={s.card}>
        <div className={s.titleRow}>
          <span className={s.title}>ML-KEM 安全信道</span>
          <button
            className={s.toggle}
            disabled
            role="switch"
            aria-checked={false}
            title="请先输入板卡密码"
          >
            <span className={s.toggleThumb} />
          </button>
        </div>
        <div className={s.disabledRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.muted}>请先在下方输入板卡密码</span>
        </div>
      </div>
    )
  }

  // 2) Toggle OFF (board configured)
  if (!enabled) {
    return (
      <div className={s.card}>
        <div className={s.titleRow}>
          <span className={s.title}>ML-KEM 安全信道</span>
          <button
            className={s.toggle}
            onClick={handleToggle}
            role="switch"
            aria-checked={false}
            title="点击启用 ML-KEM 加密通道"
          >
            <span className={s.toggleThumb} />
          </button>
        </div>
        <div className={s.disabledRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.muted}>ML-KEM 加密通道未启用</span>
        </div>
      </div>
    )
  }

  // 3) Toggle ON — error state
  if (isError) {
    return (
      <div className={s.card}>
        <div className={s.titleRow}>
          <span className={s.title}>ML-KEM 安全信道</span>
          <button
            className={`${s.toggle} ${s.toggleOn}`}
            onClick={handleToggle}
            role="switch"
            aria-checked={true}
            title="点击关闭 ML-KEM"
          >
            <span className={s.toggleThumb} />
          </button>
        </div>
        <div className={s.errorRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.errorText}>后量子加密通道未连接</span>
        </div>
      </div>
    )
  }

  // 4) Toggle ON — loading
  if (isLoading || !data) {
    return (
      <div className={s.card}>
        <div className={s.titleRow}>
          <span className={s.title}>ML-KEM 安全信道</span>
          <button
            className={`${s.toggle} ${s.toggleOn}`}
            onClick={handleToggle}
            role="switch"
            aria-checked={true}
          >
            <span className={s.toggleThumb} />
          </button>
        </div>
        <div className={s.loadingRow}>
          <span className={s.spinner} />
          <span className={s.muted}>正在检测...</span>
        </div>
      </div>
    )
  }

  // 5) Toggle ON — normal display
  const st = STATE_LABEL[data.channel_state] ?? { label: data.channel_state, tone: 'neutral' }

  return (
    <div className={s.card}>
      <div className={s.titleRow}>
        <span className={s.title}>ML-KEM 安全信道</span>
        <button
          className={`${s.toggle} ${s.toggleOn}`}
          onClick={handleToggle}
          role="switch"
          aria-checked={true}
          title="点击关闭 ML-KEM"
        >
          <span className={s.toggleThumb} />
        </button>
      </div>

      <div className={s.rowGrid}>
        <span className={s.label}>通道状态</span>
        <span className={s.value}>{st.label}</span>

        <span className={s.label}>KEM 后端</span>
        <span className={s.mono}>{data.kem_backend}</span>

        <span className={s.label}>密码套件</span>
        <span className={s.mono}>{data.cipher_suite}</span>

        {data.handshake_ms != null && <>
          <span className={s.label}>握手耗时</span>
          <span className={s.mono}>{data.handshake_ms.toFixed(1)} ms</span>
        </>}
        {data.encrypt_ms != null && <>
          <span className={s.label}>加密发送</span>
          <span className={s.mono}>{data.encrypt_ms.toFixed(1)} ms</span>
        </>}
        {data.decrypt_ms != null && <>
          <span className={s.label}>解密接收</span>
          <span className={s.mono}>{data.decrypt_ms.toFixed(1)} ms</span>
        </>}
        {data.inference_ms != null && <>
          <span className={s.label}>TVM 推理</span>
          <span className={s.mono}>{data.inference_ms.toFixed(1)} ms</span>
        </>}

        {(data.bytes_sent != null || data.bytes_received != null) && <>
          <span className={s.label}>加密流量</span>
          <span className={s.mono}>↑{data.bytes_sent ?? 0}B / ↓{data.bytes_received ?? 0}B</span>
        </>}

        {(data.control_guard_state || data.control_last_fault_code) && <>
          <span className={s.label}>控制面</span>
          <span className={s.mono}>
            {data.control_guard_state ?? 'UNKNOWN'} / {data.control_last_fault_code ?? 'UNKNOWN'}
          </span>
        </>}

        {(data.control_heartbeat_ok != null || data.control_total_fault_count != null) && <>
          <span className={s.label}>HB / 故障</span>
          <span className={s.mono}>{data.control_heartbeat_ok ?? 0} / {data.control_total_fault_count ?? 0}</span>
        </>}

        {(data.control_job_req_count != null
          || data.control_job_admit_count != null
          || data.control_job_reject_count != null) && <>
          <span className={s.label}>JOB</span>
          <span className={s.mono}>
            REQ={data.control_job_req_count ?? 0} ALLOW={data.control_job_admit_count ?? 0} DENY={data.control_job_reject_count ?? 0}
          </span>
        </>}

        {(data.control_heartbeat_event_count != null
          || data.control_heartbeat_lost_count != null
          || data.control_safe_stop_triggered_count != null
          || data.control_safe_stop_cleared_count != null) && <>
          <span className={s.label}>事件</span>
          <span className={s.mono}>
            HB={data.control_heartbeat_event_count ?? 0}(lost={data.control_heartbeat_lost_count ?? 0}) STOP={data.control_safe_stop_triggered_count ?? 0}→{data.control_safe_stop_cleared_count ?? 0}
          </span>
        </>}

        {data.control_recover_attempted && data.control_recover_note && <>
          <span className={s.label}>恢复</span>
          <span className={s.muted}>{data.control_recover_note}</span>
        </>}

        {data.last_sha256_match != null && <>
          <span className={s.label}>SHA256</span>
          <span className={data.last_sha256_match ? s.ok : s.fail}>
            {data.last_sha256_match ? '✓ 匹配' : '✗ 不匹配'}
          </span>
        </>}

        {data.session_count != null && data.session_count > 0 && <>
          <span className={s.label}>累计会话</span>
          <span className={s.mono}>{data.session_count}</span>
        </>}

        {data.error && <>
          <span className={s.label}>错误</span>
          <span className={s.muted}>{data.error}</span>
        </>}

        {data.batch_status === 'running' && <>
          <span className={s.label}>批量推理</span>
          <span className={s.mono}>{data.batch_completed ?? 0} / {data.batch_total ?? '?'} 运行中...</span>
        </>}
      </div>

      {/* Batch benchmark results */}
      {data.batch_status === 'done' && data.batch_benchmark && (() => {
        const bm = data.batch_benchmark
        const rows: { label: string; key: keyof typeof bm }[] = [
          { label: '握手', key: 'handshake_ms' },
          { label: '加密', key: 'encrypt_ms' },
          { label: '解密', key: 'decrypt_ms' },
          { label: '推理', key: 'inference_ms' },
          { label: '总计', key: 'total_ms' },
        ]
        const validRows = rows.filter(r => bm[r.key] != null)
        if (validRows.length === 0) return null
        return (
          <div className={s.benchSection}>
            <div className={s.benchTitle}>
              批量 Benchmark ({bm.total_ms?.n ?? data.batch_completed ?? '?'} 张)
            </div>
            <table className={s.benchTable}>
              <thead>
                <tr>
                  <th>阶段</th>
                  <th>均值</th>
                  <th>中位</th>
                  <th>p95</th>
                </tr>
              </thead>
              <tbody>
                {validRows.map(({ label, key }) => {
                  const m = bm[key]!
                  return (
                    <tr key={key}>
                      <td>{label}</td>
                      <td>{m.mean_ms} ms</td>
                      <td>{m.median_ms} ms</td>
                      <td>{m.p95_ms != null ? `${m.p95_ms} ms` : '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      })()}

      <div className={s.testSection}>
        <button
          className={s.testBtn}
          onClick={handleTest}
          disabled={testing}
        >
          {testing ? <span className={s.spinner} /> : '测试加密通道'}
        </button>
        {testResult && (
          <span className={testResult.ok ? s.ok : s.fail}>
            {testResult.msg}
          </span>
        )}
      </div>
    </div>
  )
}
