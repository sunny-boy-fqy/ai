#!/bin/bash
# AI CLI 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/ai"
VENV_PATH="$CONFIG_DIR/python_venv"

# 检查虚拟环境
if [ -d "$VENV_PATH" ]; then
    PYTHON="$VENV_PATH/bin/python3"
else
    PYTHON="/usr/bin/python3"
fi

# 运行
exec "$PYTHON" "$SCRIPT_DIR/ai.py" "$@"
