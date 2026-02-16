#!/bin/bash

# AI CLI 安装脚本
# 从 https://github.com/sunny-boy-fqy/ai 安装

set -e

REPO_URL="https://github.com/sunny-boy-fqy/ai.git"
TARGET_DIR="$HOME/ai"
CONFIG_DIR="$HOME/.config/ai"
VENV_PATH="$CONFIG_DIR/python_venv"
NODE_DIR="$CONFIG_DIR/node_venv"
MCP_DIR="$CONFIG_DIR/mcp"

echo "=== 🤖 AI CLI 安装程序 ==="

# ========== 1. 检查系统依赖 ==========
check_dependencies() {
    echo "检查系统依赖..."
    local missing=()
    
    command -v curl &> /dev/null || missing+=("curl")
    command -v git &> /dev/null || missing+=("git")
    command -v python3 &> /dev/null || missing+=("python3")
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo "缺失依赖: ${missing[*]}"
        
        if command -v apt &> /dev/null; then
            echo "使用 apt 安装..."
            sudo apt update
            sudo apt install -y git python3 python3-venv python3-pip curl
        elif command -v dnf &> /dev/null; then
            echo "使用 dnf 安装..."
            sudo dnf install -y git python3 python3-pip curl
        elif command -v pacman &> /dev/null; then
            echo "使用 pacman 安装..."
            sudo pacman -S --noconfirm git python curl
        else
            echo "❌ 请手动安装: ${missing[*]}"
            exit 1
        fi
    fi
}

check_dependencies

# ========== 2. 确定安装目录 ==========
if [ -f "$CONFIG_DIR/base_path.config" ]; then
    DEFAULT_DIR=$(cat "$CONFIG_DIR/base_path.config")
else
    DEFAULT_DIR="$HOME/ai"
fi

if [ -t 0 ]; then
    read -p "安装路径 [$DEFAULT_DIR]: " INPUT_DIR
    TARGET_DIR="${INPUT_DIR:-$DEFAULT_DIR}"
else
    TARGET_DIR="$DEFAULT_DIR"
fi

TARGET_DIR="${TARGET_DIR/#\~/$HOME}"

# ========== 3. 下载仓库 ==========
echo "下载 AI CLI..."
if [ -d "$TARGET_DIR/.git" ]; then
    cd "$TARGET_DIR"
    git pull
else
    git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# ========== 4. 创建目录结构 ==========
echo "创建目录结构..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$CONFIG_DIR/config"
mkdir -p "$CONFIG_DIR/history"
mkdir -p "$CONFIG_DIR/mcp"
mkdir -p "$CONFIG_DIR/task_logs"

# 写入基础路径
echo "$TARGET_DIR" > "$CONFIG_DIR/base_path.config"

# ========== 5. 安装本地 Node.js ==========
if [ ! -f "$NODE_DIR/bin/node" ]; then
    echo "安装本地 Node.js..."
    
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) NODE_ARCH="linux-x64" ;;
        aarch64) NODE_ARCH="linux-arm64" ;;
        *) echo "❌ 不支持的架构: $ARCH"; exit 1 ;;
    esac
    
    NODE_VERSION="v20.11.1"
    NODE_URL="https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-$NODE_ARCH.tar.xz"
    
    TEMP_FILE="/tmp/node.tar.xz"
    curl -L "$NODE_URL" -o "$TEMP_FILE"
    
    mkdir -p "$NODE_DIR"
    tar -xJf "$TEMP_FILE" -C "$NODE_DIR" --strip-components=1
    rm "$TEMP_FILE"
    
    echo "✅ Node.js 安装完成"
fi

LOCAL_NODE="$NODE_DIR/bin/node"
LOCAL_NPX="$NODE_DIR/bin/npx"

# ========== 6. 创建 Python 虚拟环境 ==========
if [ ! -d "$VENV_PATH" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_PATH"
fi

# ========== 7. 安装 Python 依赖 ==========
echo "安装 Python 依赖..."
"$VENV_PATH/bin/pip" install --upgrade pip -q
"$VENV_PATH/bin/pip" install openai zhipuai groq httpx mcp pydantic tqdm requests duckduckgo_search -q

# ========== 8. 创建 MCP 配置 ==========
MCP_CONFIG="$MCP_DIR/mcp.config"
if [ ! -f "$MCP_CONFIG" ]; then
    cat > "$MCP_CONFIG" <<EOF
{
  "servers": {
    "filesystem": {
      "command": "$LOCAL_NPX",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
EOF
fi

# ========== 9. 设置别名 ==========
BASHRC="$HOME/.bashrc"
START_SCRIPT="$TARGET_DIR/start.sh"
ALIAS_LINE="alias ai='$START_SCRIPT'"

chmod +x "$START_SCRIPT"

if grep -q "alias ai=" "$BASHRC"; then
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
else
    echo "" >> "$BASHRC"
    echo "# AI CLI" >> "$BASHRC"
    echo "$ALIAS_LINE" >> "$BASHRC"
fi

# ========== 10. 完成 ==========
echo ""
echo "✅ 安装完成！版本 0.2.0"
echo ""
echo "使用方法:"
echo "  source ~/.bashrc"
echo "  ai              # 显示帮助"
echo "  ai new          # 创建供应商"
echo "  ai ask 你好     # 即时问答"
echo "  ai chat         # 对话模式"
echo ""
echo "Leader-Worker 模式:"
echo "  cd your-project"
echo "  ai init --auto  # 初始化项目"
echo "  ai work         # 进入工作模式"
echo "  ai work --debug # 调试模式"
echo "  ai work --resume # 恢复未完成任务"
echo ""
echo "新功能 (v0.2.0):"
echo "  • API 调用自动重试"
echo "  • 智能上下文压缩"
echo "  • 任务恢复功能"
echo "  • 并行任务执行"
echo "  • 进度可视化"
echo ""
