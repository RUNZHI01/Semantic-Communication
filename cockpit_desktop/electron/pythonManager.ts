import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export type BackendOptions = {
  host?: string
  port?: number
}

export type RunningBackend = {
  process: ChildProcess
}

function resolveRepoRoot(): string {
  const fromMain = path.resolve(__dirname, '../../..')
  const envRoot = process.env.COCKPIT_REPO_ROOT?.trim()
    ? path.resolve(process.env.COCKPIT_REPO_ROOT)
    : ''

  for (const root of [fromMain, envRoot].filter(Boolean)) {
    const server = path.join(
      root,
      'session_bootstrap',
      'demo',
      'openamp_control_plane_demo',
      'server.py',
    )
    if (existsSync(server)) {
      return root
    }
  }

  throw new Error(
    '找不到仓库根目录（未找到 session_bootstrap/demo/openamp_control_plane_demo/server.py）。' +
      '请从仓库内 cockpit_desktop 运行，或设置环境变量 COCKPIT_REPO_ROOT。',
  )
}

export function startPythonBackend(options: BackendOptions = {}): RunningBackend | null {
  if (process.env.COCKPIT_SKIP_PYTHON === '1') {
    console.warn('[cockpit-desktop] COCKPIT_SKIP_PYTHON=1，跳过启动 Python 后端')
    return null
  }

  const host = options.host ?? process.env.COCKPIT_BACKEND_HOST ?? '127.0.0.1'
  const port = options.port ?? Number(process.env.COCKPIT_BACKEND_PORT ?? 8079)

  const repoRoot = resolveRepoRoot()
  const cwd = path.join(repoRoot, 'session_bootstrap', 'demo', 'openamp_control_plane_demo')
  const script = path.join(cwd, 'server.py')

  const child = spawn('python3', [script, '--host', host, '--port', String(port)], {
    cwd,
    stdio: 'inherit',
    env: { ...process.env },
  })

  child.on('error', (err) => {
    console.error('[cockpit-desktop] Python 后端进程 error:', err)
  })

  return { process: child }
}

export function stopPythonBackend(backend: RunningBackend | null): void {
  if (!backend?.process || backend.process.killed) {
    return
  }
  backend.process.kill('SIGTERM')
}
