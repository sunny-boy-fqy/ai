#!/bin/bash
# AI CLI 启动脚本

# -----------------------------------------------------------------------------
# 1. 路径解析 (Symlink Resolution)
# -----------------------------------------------------------------------------
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
SCRIPT_DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"

# -----------------------------------------------------------------------------
# 2. 配置定义
# -----------------------------------------------------------------------------
CONFIG_DIR="$HOME/.config/ai"
VENV_PATH="$CONFIG_DIR/python_venv"
NODE_VENV="$CONFIG_DIR/node_venv"

# 调试模式: 使用 DEBUG=1 ai ... 开启
if [ -n "$DEBUG" ]; then
    echo "[DEBUG] Script Source: $SOURCE"
    echo "[DEBUG] Script Dir:    $SCRIPT_DIR"
    echo "[DEBUG] Config Dir:    $CONFIG_DIR"
fi

# -----------------------------------------------------------------------------
# 3. 环境检查与设置
# -----------------------------------------------------------------------------

# 3.1 Node.js 环境设置
# install.sh 安装了本地 node 到 ~/.config/ai/node_venv
# 我们需要将其加入 PATH，以便 ai.py 和子进程能找到 node/npx
if [ -d "$NODE_VENV/bin" ]; then
    if [ -n "$DEBUG" ]; then echo "[DEBUG] Adding Node.js to PATH: $NODE_VENV/bin"; fi
    export PATH="$NODE_VENV/bin:$PATH"
fi

# 3.2 Python 环境选择 (支持回退到系统 Python)
if [ -f "$VENV_PATH/bin/python3" ]; then
    PYTHON_BIN="$VENV_PATH/bin/python3"
    if [ -n "$DEBUG" ]; then echo "[DEBUG] Using venv python: $PYTHON_BIN"; fi
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    # 仅在非 DEBUG 模式下显示警告 (DEBUG 模式下已显示路径)
    if [ -n "$DEBUG" ]; then 
        echo "[DEBUG] Venv not found, using system python: $PYTHON_BIN"
    else
        echo "⚠️  警告: 未找到虚拟环境，尝试使用系统 Python..." >&2
    fi
else
    echo "❌ 错误: 未找到 Python 环境。" >&2
    echo "   请尝试运行安装脚本: bash $SCRIPT_DIR/install.sh" >&2
    exit 1
fi

# 3.3 主程序检查
AI_SCRIPT="$SCRIPT_DIR/ai.py"
if [ ! -f "$AI_SCRIPT" ]; then
    echo "❌ 错误: 未找到 ai.py 主程序。" >&2
    echo "   路径: $AI_SCRIPT" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# 4. 执行
# -----------------------------------------------------------------------------
if [ -n "$DEBUG" ]; then echo "[DEBUG] Executing: $PYTHON_BIN $AI_SCRIPT $@"; fi

exec "$PYTHON_BIN" "$AI_SCRIPT" "$@"
