import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('cockpit', {
  platform: process.platform,
})
