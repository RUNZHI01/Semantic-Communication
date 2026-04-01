/// <reference types="vite/client" />

export type CockpitPreload = {
  platform: NodeJS.Platform
}

declare global {
  interface Window {
    cockpit?: CockpitPreload
  }
}

export {}
