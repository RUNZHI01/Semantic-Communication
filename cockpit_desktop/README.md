# Cockpit Desktop

基于 **Electron + Vite + React 18 + TypeScript + Ant Design 5** 的上位机座舱演示，消费 `session_bootstrap/demo/openamp_control_plane_demo/server.py` HTTP API。

## 开发

```bash
cd cockpit_desktop
npm install
npm run dev
```

## 运行要求

- 需要放在完整仓库里运行，不是只拷贝 `cockpit_desktop/` 一个子目录；Electron 会启动同仓库下的 `session_bootstrap/demo/openamp_control_plane_demo/server.py`
- 主机至少需要 `python3` 或 `python`
- 真机链路相关流程依赖 `bash`、`ssh`；若有 `sshpass` 会优先使用，没有也会退回到 `SSH_ASKPASS`

## 常用环境变量

- `COCKPIT_REPO_ROOT`: 显式指定仓库根目录
- `COCKPIT_SERVER_SCRIPT`: 显式指定后端 `server.py` 路径
- `COCKPIT_PYTHON`: 显式指定 Python 可执行文件
- `COCKPIT_BACKEND_HOST` / `COCKPIT_BACKEND_PORT`: 指定 Electron 与 Vite 使用的后端地址
- `COCKPIT_SKIP_PYTHON=1`: 已有外部后端时，跳过 Electron 自动拉起 Python

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
