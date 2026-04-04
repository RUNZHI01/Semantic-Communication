import { useCryptoStatus } from '../../../hooks/useCryptoStatus'
import s from './CryptoStatusPanel.module.css'

const STATE_LABEL: Record<string, { label: string; tone: string }> = {
  idle: { label: '空闲', tone: 'neutral' },
  handshaking: { label: '握手中', tone: 'warn' },
  ready: { label: '已建立', tone: 'ok' },
  closed: { label: '已关闭', tone: 'off' },
}

export function CryptoStatusPanel() {
  const { data, isLoading, isError } = useCryptoStatus()

  if (isError) {
    return (
      <div className={s.card}>
        <div className={s.title}>ML-KEM 安全信道</div>
        <div className={s.errorRow}>
          <span className={`${s.dot} ${s.dotOff}`} />
          <span className={s.errorText}>后量子加密通道未连接</span>
        </div>
      </div>
    )
  }

  if (isLoading || !data) {
    return (
      <div className={s.card}>
        <div className={s.title}>ML-KEM 安全信道</div>
        <div className={s.loadingRow}>
          <span className={s.spinner} />
          <span className={s.muted}>正在检测…</span>
        </div>
      </div>
    )
  }

  const st = STATE_LABEL[data.channel_state] ?? { label: data.channel_state, tone: 'neutral' }
  const dotClass =
    st.tone === 'ok' ? s.dotOk :
    st.tone === 'warn' ? s.dotWarn :
    st.tone === 'off' ? s.dotOff : s.dotNeutral

  return (
    <div className={s.card}>
      <div className={s.title}>ML-KEM 安全信道</div>

      {/* Row 1: channel state */}
      <div className={s.row}>
        <span className={`${s.dot} ${dotClass}`} />
        <span className={s.label}>通道状态</span>
        <span className={s.value}>{st.label}</span>
      </div>

      {/* Row 2: KEM backend */}
      <div className={s.row}>
        <span className={s.label}>KEM 后端</span>
        <span className={s.mono}>{data.kem_backend}</span>
      </div>

      {/* Row 3: cipher suite */}
      <div className={s.row}>
        <span className={s.label}>密码套件</span>
        <span className={s.mono}>{data.cipher_suite}</span>
      </div>

      {/* Row 4: performance (conditional) */}
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

      {/* Row 5: integrity */}
      {data.last_sha256_match != null && (
        <div className={s.row}>
          <span className={s.label}>SHA256 完整性</span>
          <span className={data.last_sha256_match ? s.ok : s.fail}>
            {data.last_sha256_match ? '✓ 匹配' : '✗ 不匹配'}
          </span>
        </div>
      )}

      {/* Row 6: session stats */}
      {data.session_count != null && data.session_count > 0 && (
        <div className={s.row}>
          <span className={s.label}>累计会话</span>
          <span className={s.mono}>{data.session_count}</span>
        </div>
      )}
    </div>
  )
}
