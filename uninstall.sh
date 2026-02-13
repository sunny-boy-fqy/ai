#!/bin/bash

# AI CLI 卸载脚本

CONFIG_DIR="$HOME/.config/ai"
BASHRC="$HOME/.bashrc"

echo "=== 🤖 AI CLI 卸载程序 ==="

if [ "$1" != "-y" ]; then
    echo "警告：此操作将删除："
    echo "  - $CONFIG_DIR (所有配置、API密钥、历史记录)"
    echo "  - ~/ai (程序文件)"
    echo "  - ~/.bashrc 中的 alias"
    echo
    read -p "确定要卸载吗？(y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "已取消"
        exit 0
    fi
fi

# 停止任务守护进程
PID_FILE="$CONFIG_DIR/task_daemon.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "停止任务守护进程..."
        kill "$PID" 2>/dev/null
    fi
fi

# 删除配置目录
if [ -d "$CONFIG_DIR" ]; then
    echo "删除配置目录..."
    rm -rf "$CONFIG_DIR"
fi

# 删除程序目录
if [ -d "$HOME/ai" ]; then
    echo "删除程序目录..."
    rm -rf "$HOME/ai"
fi

# 删除别名
if [ -f "$BASHRC" ]; then
    echo "删除别名..."
    sed -i '/# AI CLI/d' "$BASHRC"
    sed -i '/alias ai=/d' "$BASHRC"
fi

echo
echo "✅ 卸载完成"
echo "运行 'source ~/.bashrc' 刷新环境"
