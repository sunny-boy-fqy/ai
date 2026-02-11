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
    for cmd in git python3 curl; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done

    # 检查 python3-venv (Debian/Ubuntu 特有)
    if command -v python3 &> /dev/null; then
        if ! python3 -m venv --help &> /dev/null; then
            missing_deps+=("python3-venv")
        fi
    fi

    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "检测到缺失依赖: ${missing_deps[*]}"
        if command -v apt &> /dev/null; then
            echo "尝试使用 sudo apt 安装依赖..."
            sudo apt update
            sudo apt install -y git python3 python3-venv curl
        else
            echo "❌ 无法自动安装依赖。请手动安装: ${missing_deps[*]}"
            exit 1
        fi
    fi
}

check_dependencies

# 2. 仓库克隆或下载
if [ -d "$TARGET_DIR/.git" ]; then
    REPO_DIR="$TARGET_DIR"
    cd "$REPO_DIR"
    if command -v git &> /dev/null; then
        echo "正在检查更新..."
        git fetch origin &>/dev/null
        LOCAL=$(git rev-parse HEAD)
        UPSTREAM=${1:-'@{u}'}
        REMOTE=$(git rev-parse "$UPSTREAM" 2>/dev/null || echo "$LOCAL")
        
        if [ "$LOCAL" != "$REMOTE" ] || [ "$1" == "--upgrade" ]; then
            echo "正在更新到最新版本..."
            git pull
        else
            echo "已经是最新版本。"
        fi
    else
        echo "ℹ️ 仓库已存在但未检测到 git，跳过更新。"
    fi
else
    # 如果当前就在 ai 目录内且有核心文件，则不克隆
    if [ -f "ai_caller.py" ] && [ -f "install.sh" ]; then
        REPO_DIR="$(pwd)"
    else
        if command -v git &> /dev/null; then
            echo "正在克隆仓库到 $TARGET_DIR ..."
            git clone "$REPO_URL" "$TARGET_DIR"
            REPO_DIR="$TARGET_DIR"
        else
            echo "⚠️ 未检测到 git，尝试下载 ZIP 压缩包..."
            ZIP_URL="https://github.com/sunny-boy-fqy/ai/archive/refs/heads/main.zip"
            mkdir -p "$TARGET_DIR"
            TEMP_ZIP="/tmp/ai-main.zip"
            curl -L "$ZIP_URL" -o "$TEMP_ZIP"
            if command -v unzip &> /dev/null; then
                unzip -o "$TEMP_ZIP" -d /tmp/ai-temp
                cp -r /tmp/ai-temp/ai-main/* "$TARGET_DIR/"
                rm -rf /tmp/ai-temp "$TEMP_ZIP"
                REPO_DIR="$TARGET_DIR"
                echo "✅ 已通过 ZIP 下载源码。"
            else
                echo "❌ 缺少 unzip 命令，无法解压。请手动安装 git 或 unzip。"
                exit 1
            fi
        fi
        # 下载/克隆后跳转到新目录重新执行，确保环境完整
        cd "$REPO_DIR"
        exec bash "$REPO_DIR/install.sh" "$@"
    fi
fi

# 3. 目录设置
echo "确保目录存在..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$MCP_SERVERS_DIR"

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
      "command": "npx",
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
ALIAS_LINE="alias ai='$AI_RUN_SCRIPT'"
if grep -q "alias ai=" "$BASHRC"; then
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
else
    echo -e "\n# AI Shortcut\n$ALIAS_LINE" >> "$BASHRC"
fi

# 9. 权限与完成
chmod +x "$AI_RUN_SCRIPT" "$REPO_DIR/uninstall.sh" "$REPO_DIR/install.sh"
echo -e "\n✅ 安装/更新完成！"
echo "当前版本: $(cat "$REPO_DIR/version.txt" 2>/dev/null || echo 'v0.1')"
echo "请执行: source ~/.bashrc"
