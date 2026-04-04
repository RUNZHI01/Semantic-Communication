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

  return (
    <div className={s.card}>
      <div className={s.titleRow}>
        <span className={s.title}>ML-KEM 安全信道</span>
        <button
          className={`${s.toggle} ${enabled ? s.toggleOn : ''}`}
          onClick={handleToggle}
          role="switch"
          aria-checked={enabled}
          title={enabled ? '点击关闭 ML-KEM' : '点击启用 ML-KEM'}
        >
          <span className={s.toggleThumb} />
        </button>
      </div>

      {!enabled ? (
        <div className={s.disabledRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.muted}>ML-KEM 加密通道未启用</span>
        </div>
      ) : isError ? (
        <div className={s.errorRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.errorText}>后量子加密通道未连接</span>
        </div>
      ) : isLoading || !data ? (
        <div className={s.loadingRow}>
          <span className={s.spinner} />
          <span className={s.muted}>正在检测…</span>
        </div>
      ) : (
        <>
          {(() => {
            const st = STATE_LABEL[data.channel_state] ?? { label: data.channel_state, tone: 'neutral' }
            const dotClass =
              st.tone === 'ok' ? s.dotOk :
              st.tone === 'warn' ? s.dotWarn :
              st.tone === 'off' ? s.dotOff : s.dotNeutral
            return (
              <>
                <div className={s.row}>
                  <span className={`${s.dot} ${dotClass}`} />
                  <span className={s.label}>通道状态</span>
                  <span className={s.value}>{st.label}</span>
                </div>

                <div className={s.row}>
                  <span className={s.label}>KEM 后端</span>
                  <span className={s.mono}>{data.kem_backend}</span>
                </div>

                <div className={s.row}>
                  <span className={s.label}>密码套件</span>
                  <span className={s.mono}>{data.cipher_suite}</span>
                </div>

                {data.handshake_ms != null && (
                  <div className={s.row}>
                    <span className={s.label}>握手耗时</span>
                    <span className={s.mono}>{data.handshake_ms.toFixed(1)} ms</span>
                  </div>
                )}
                {data.inference_ms != null && (
                  <div className={s.row}>
                    <span className={s.label}>TVM 推理</span>
                    <span className={s.mono}>{data.inference_ms.toFixed(1)} ms</span>
                  </div>
                )}

                {data.last_sha256_match != null && (
                  <div className={s.row}>
                    <span className={s.label}>SHA256 完整性</span>
                    <span className={data.last_sha256_match ? s.ok : s.fail}>
                      {data.last_sha256_match ? '[OK] 匹配' : '[FAIL] 不匹配'}
                    </span>
                  </div>
                )}

                {data.session_count != null && data.session_count > 0 && (
                  <div className={s.row}>
                    <span className={s.label}>累计会话</span>
                    <span className={s.mono}>{data.session_count}</span>
                  </div>
                )}
              </>
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
        </>
      )}
    </div>
  )
}
