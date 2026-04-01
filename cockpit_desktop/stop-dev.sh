#!/bin/bash
# Cockpit Desktop 开发环境停止脚本

echo "🛑 停止 Cockpit Desktop 开发环境..."

# 停止前端（Vite默认端口5173）
FRONTEND_PIDS=$(lsof -ti :5173 || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "⏹️  停止前端..."
    kill -9 $FRONTEND_PIDS 2>/dev/null || true
else
    echo "ℹ️  前端未运行"
fi

# 停止后端（8000端口）
BACKEND_PIDS=$(lsof -ti :8000 || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "⏹️  停止后端..."
    kill -9 $BACKEND_PIDS 2>/dev/null || true
else
    echo "ℹ️  后端未运行"
fi

# 清理npm和node进程
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# 清理可能的Python进程
pkill -f "server.py" 2>/dev/null || true

echo "✅ 所有服务已停止"
