# Cockpit Desktop

基于 **Electron + Vite + React 18 + TypeScript + Ant Design 5** 的上位机座舱演示，消费 `session_bootstrap/demo/openamp_control_plane_demo/server.py` HTTP API。

## 开发

```bash
cd cockpit_desktop
npm install
npm run dev
```

## 目录

- `electron/` — 主进程、预加载、pythonManager
- `src/renderer/` — React 应用
  - `components/dashboard/` — 仪表盘页面组件
    - `FlightPanel/` — 战术地图 + 遥测
    - `SidebarPanel/` — 链路/安全/引导/闸机/事件
    - `MissionStagePanel/` — 执行模式/遥测/快照/推理/对比
    - `ActionToolbar/` — 操作按钮栏
  - `components/shared/` — PanelCard, ToneTag, EmptyState
  - `components/ios/` — IOSTag, IOSSwitch, IOSProgress
  - `components/charts/` — PerformanceGauge, InferenceTimeline
  - `components/WorldMapStage/` — 战术地图 Canvas
  - `theme/` — tokens.ts (design tokens), echarts-theme.ts
- `public/geo/` — GeoJSON 地图数据
