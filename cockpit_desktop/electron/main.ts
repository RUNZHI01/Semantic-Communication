import { app, BrowserWindow } from 'electron'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { startPythonBackend, stopPythonBackend, type RunningBackend } from './pythonManager'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

let mainWindow: BrowserWindow | null = null
let backend: RunningBackend | null = null

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 2560,
    height: 1440,
    show: false,
    backgroundColor: '#F0F4F9',
    webPreferences: {
      // electron-vite 在 type:module 下产出 out/preload/index.mjs
      preload: path.join(__dirname, '../preload/index.mjs'),
      contextIsolation: true,
      sandbox: false,
    },
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow?.webContents.setZoomFactor(WSL_SCALE)
    mainWindow?.show()
    // Open DevTools in development to debug issues
    mainWindow?.webContents.openDevTools()
  })

  if (process.env.ELECTRON_RENDERER_URL) {
    void mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
}

// Disable GPU acceleration for WSL compatibility
app.disableHardwareAcceleration()

// WSLg reports 100% scaling; override to match host DPI
const WSL_SCALE = Number(process.env.WSL_SCALE_FACTOR ?? '1.25')

app.whenReady().then(() => {
  backend = startPythonBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', () => {
  stopPythonBackend(backend)
  backend = null
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
