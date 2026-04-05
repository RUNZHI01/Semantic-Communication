/**
 * ML-KEM crypto channel status — returned by /api/crypto-status
 */

export type CryptoChannelState = 'idle' | 'handshaking' | 'ready' | 'closed' | 'disabled'

export type CryptoStatusResponse = {
  /** KEM backend name, e.g. "tongsuo-ML-KEM-768" or "liboqs-ML-KEM-768" */
  kem_backend: string
  /** Cipher suite, e.g. "aes-256-gcm" */
  cipher_suite: string
  /** Channel state */
  channel_state: CryptoChannelState
  /** Last handshake duration in ms */
  handshake_ms?: number
  /** Last encrypt+send duration in ms */
  encrypt_ms?: number
  /** Last decrypt duration in ms */
  decrypt_ms?: number
  /** Last TVM inference duration in ms */
  inference_ms?: number
  /** Total bytes sent (encrypted) */
  bytes_sent?: number
  /** Total bytes received (encrypted) */
  bytes_received?: number
  /** Last SHA256 integrity check result */
  last_sha256_match?: boolean
  /** Last session timestamp */
  last_session_at?: string
  /** Number of completed sessions */
  session_count?: number
  /** Error message if any */
  error?: string
  /** Whether ML-KEM is enabled via toggle */
  enabled: boolean
  /** Whether board credentials have been entered */
  board_configured: boolean
  /** Control-plane guard state snapshot from latest OpenAMP status */
  control_guard_state?: string
  /** Control-plane last fault snapshot */
  control_last_fault_code?: string
  /** Heartbeat acknowledgement counter from control status */
  control_heartbeat_ok?: number
  /** Total fault counter from control status */
  control_total_fault_count?: number
  /** Whether a soft recover was attempted before blocking */
  control_recover_attempted?: boolean
  /** Soft recover note for operator context */
  control_recover_note?: string
}

export type CryptoTestResult = {
  status: 'ok' | 'error'
  message?: string
  handshake_ms?: number
  sha256_match?: boolean
  wall_ms?: number
}
