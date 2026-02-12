#!/bin/bash

# AI Tool Installation & Update Script

TARGET_DIR="$HOME/ai"
CONFIG_DIR="$HOME/.config/ai"
USER_AI_DIR="$HOME/.ai"
MCP_SERVERS_DIR="$USER_AI_DIR/mcp_servers"
VENV_PATH="$CONFIG_DIR/python_venv"
REPO_URL="https://github.com/sunny-boy-fqy/ai.git"

echo "=== 🤖 AI CLI Installation/Update ==="

# 1. 检查并安装系统依赖
check_dependencies() {
    local missing_deps=()
    echo "正在检查系统环境..."

    if ! command -v curl &> /dev/null; then missing_deps+=("curl"); fi
    if ! command -v git &> /dev/null; then missing_deps+=("git"); fi

    # 检查 python3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        # 检查 venv 模块是否可用 (Debian/Ubuntu 经常将其拆分)
        if ! python3 -m venv --help &> /dev/null; then
            missing_deps+=("python3-venv")
        fi
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "检测到缺失依赖: ${missing_deps[*]}"
        if command -v apt &> /dev/null; then
            echo "尝试使用 sudo apt 自动安装依赖 (可能需要输入密码)..."
            sudo apt update
            sudo apt install -y git python3 python3-venv curl python3-pip
        elif command -v dnf &> /dev/null; then
            echo "尝试使用 sudo dnf 自动安装依赖..."
            sudo dnf install -y git python3 curl
        elif command -v pacman &> /dev/null; then
            echo "尝试使用 sudo pacman 自动安装依赖..."
            sudo pacman -S --noconfirm git python curl
        else
            echo "❌ 无法自动为您的系统安装依赖。请手动安装: ${missing_deps[*]}"
            exit 1
        fi
        
        # 再次检查
        if ! command -v python3 &> /dev/null || ! python3 -m venv --help &> /dev/null; then
            echo "❌ 依赖安装失败，请手动解决 Python3 环境问题后再运行。"
            exit 1
        fi
    fi
}

check_dependencies

# 2. 确定安装路径
CONFIG_DIR="$HOME/.config/ai"
if [ -f "$CONFIG_DIR/base_path.config" ]; then
    DEFAULT_DIR=$(cat "$CONFIG_DIR/base_path.config")
else
    DEFAULT_DIR="$HOME/ai"
fi

read -p "请输入安装路径 [默认: $DEFAULT_DIR]: " INPUT_DIR
TARGET_DIR=${INPUT_DIR:-$DEFAULT_DIR}
TARGET_DIR="${TARGET_DIR/#\~/$HOME}"
REPO_DIR="$TARGET_DIR"

# 3. 仓库下载
if [ -d "$TARGET_DIR/.git" ]; then
    cd "$TARGET_DIR"
    if command -v git &> /dev/null; then
        echo "正在检查更新..."
        git pull
    fi
else
    if [ -f "ai_caller.py" ] && [ -f "install.sh" ] && [ "$(pwd)" == "$TARGET_DIR" ]; then
        echo "当前已在目标目录。"
    else
        mkdir -p "$TARGET_DIR"
        if command -v git &> /dev/null; then
            git clone "$REPO_URL" "$TARGET_DIR"
        else
            ZIP_URL="https://github.com/sunny-boy-fqy/ai/archive/refs/heads/main.zip"
            TEMP_ZIP="/tmp/ai-main.zip"
            curl -L "$ZIP_URL" -o "$TEMP_ZIP"
            unzip -o "$TEMP_ZIP" -d /tmp/ai-temp
            cp -r /tmp/ai-temp/ai-main/* "$TARGET_DIR/"
            rm -rf /tmp/ai-temp "$TEMP_ZIP"
        fi
    fi
fi

# 确保脚本权限
cd "$REPO_DIR"

# 4. 目录设置
echo "确保目录存在..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$MCP_SERVERS_DIR"
echo "$REPO_DIR" > "$CONFIG_DIR/base_path.config"
NODE_LOCAL_DIR="$CONFIG_DIR/node"

# 5. 本地 Node.js 安装 (零污染方案)
if [ ! -f "$NODE_LOCAL_DIR/bin/node" ]; then
    echo "正在为 MCP 工具安装本地私有 Node.js (不会影响系统环境)..."
    ARCH=$(uname -m)
    if [ "$ARCH" == "x86_64" ]; then NODE_ARCH="linux-x64";
    elif [ "$ARCH" == "aarch64" ]; then NODE_ARCH="linux-arm64";
    else echo "❌ 不支持的架构: $ARCH"; exit 1; fi
    
    NODE_VERSION="v20.11.1"
    NODE_URL="https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-$NODE_ARCH.tar.xz"
    
    TEMP_TAR="/tmp/node.tar.xz"
    curl -L "$NODE_URL" -o "$TEMP_TAR"
    mkdir -p "$NODE_LOCAL_DIR"
    tar -xJf "$TEMP_TAR" -C "$NODE_LOCAL_DIR" --strip-components=1
    rm "$TEMP_TAR"
    echo "✅ 本地 Node.js 安装完成。"
fi

LOCAL_NODE="$NODE_LOCAL_DIR/bin/node"
LOCAL_NPX="$NODE_LOCAL_DIR/bin/npx"

# 6. 虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_PATH"
fi

# 4. 基础路径配置
echo "$REPO_DIR" > "$CONFIG_DIR/base_path.config"

# 5. 虚拟环境
if [ ! -d "$VENV_PATH" ]; then
    echo "创建 Python 虚拟环境..."
    python3 -m venv "$VENV_PATH"
fi

# 6. 安装/更新依赖
echo "安装/更新 Python 依赖..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 7. MCP 配置
echo "配置 MCP..."
MCP_CONFIG_PATH="$CONFIG_DIR/mcp_config.json"
if [ ! -f "$MCP_CONFIG_PATH" ]; then
    if [ -f "$REPO_DIR/mcp_servers/web_search_server.py" ]; then
        cp "$REPO_DIR/mcp_servers/web_search_server.py" "$MCP_SERVERS_DIR/"
    fi
    cat > "$MCP_CONFIG_PATH" <<EOF
{
  "servers": {
    "filesystem": {
      "command": "$LOCAL_NPX",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "type": "stdio"
    },
    "web-search": {
      "command": "$VENV_PATH/bin/python3",
      "args": ["$MCP_SERVERS_DIR/web_search_server.py"],
      "type": "stdio"
    }
  }
}
EOF
fi

# 8. 别名设置
BASHRC="$HOME/.bashrc"
AI_RUN_SCRIPT="$REPO_DIR/ai_run.sh"
# 确保绝对路径被正确写入
ALIAS_LINE="alias ai='$AI_RUN_SCRIPT'"

# 9. 权限与完成
chmod +x "$AI_RUN_SCRIPT" "$REPO_DIR/uninstall.sh" "$REPO_DIR/install.sh"
if grep -q "alias ai=" "$BASHRC"; then
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
else
    echo -e "\n# AI Shortcut\n$ALIAS_LINE" >> "$BASHRC"
fi
echo -e "\n✅ 安装/更新完成！"
echo "当前版本: $(cat "$REPO_DIR/version.txt" 2>/dev/null || echo 'v0.1')"
echo "请执行: source ~/.bashrc"
