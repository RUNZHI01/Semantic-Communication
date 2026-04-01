#!/bin/bash
# Cockpit Desktop 开发环境启动脚本

set -e

echo "🚀 启动 Cockpit Desktop 开发环境..."

# 1. 杀掉可能占用8000端口的进程
echo "🔍 检查8000端口..."
PORT_PID=$(lsof -ti :8000 || true)
if [ -n "$PORT_PID" ]; then
    echo "⚠️  端口8000被占用 (PID: $PORT_PID)，正在杀掉进程..."
    kill -9 $PORT_PID
    sleep 1
fi

# 2. 启动后端服务器
echo "🔧 启动后端服务器..."
cd /home/tianxing/tvm_metaschedule_execution_project
nohup python3 session_bootstrap/demo/openamp_control_plane_demo/server.py --port 8000 > /tmp/openamp-server.log 2>&1 &
SERVER_PID=$!
echo "   后端 PID: $SERVER_PID"

# 等待服务器启动并验证端口
echo "   等待后端启动..."
for i in {1..10}; do
    sleep 1
    if lsof -ti :8000 > /dev/null 2>&1; then
        # 检查是否是我们的进程
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            echo "✅ 后端服务器运行正常"
            break
        fi
    fi
    if [ $i -eq 10 ]; then
        echo "❌ 后端服务器启动失败"
        echo "   查看日志: tail /tmp/openamp-server.log"
        exit 1
    fi
    echo "   等待中... ($i/10)"
done

# 3. 启动前端开发服务器
echo "💻 启动前端开发服务器..."
cd /home/tianxing/tvm_metaschedule_execution_project/cockpit_desktop
npm run dev &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

echo ""
echo "✅ 开发环境启动完成！"
echo ""
echo "📝 进程信息:"
echo "   后端 PID: $SERVER_PID (日志: /tmp/openamp-server.log)"
echo "   前端 PID: $FRONTEND_PID"
echo ""
echo "🌐 访问地址:"
echo "   新极简界面: http://localhost:5173/#/"
echo "   旧三栏界面: http://localhost:5173/#/legacy"
echo ""
echo "🛑 停止服务:"
echo "   kill $SERVER_PID $FRONTEND_PID"
echo "   或运行: ./stop-dev.sh"
echo ""
echo "💡 提示: 按 Ctrl+C 只会停止前端，后端继续运行"
