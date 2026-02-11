#!/bin/bash

# AI Tool Installation & Update Script

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="$HOME/.config/ai"
USER_AI_DIR="$HOME/.ai"
MCP_SERVERS_DIR="$USER_AI_DIR/mcp_servers"
VENV_PATH="$CONFIG_DIR/python_venv"

echo "=== 🤖 AI CLI Installation/Update ==="

# 0. Check for Update
if [ -d "$REPO_DIR/.git" ]; then
    echo "Checking for updates..."
    cd "$REPO_DIR"
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u})
    if [ "$LOCAL" != "$REMOTE" ] || [ "$1" == "--upgrade" ]; then
        echo "Updating to latest version..."
        git pull
    else
        echo "Already at the latest version."
    fi
fi

# 1. Directory Setup
echo "Ensuring directories exist..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$MCP_SERVERS_DIR"

# 2. Base Path Config
echo "$REPO_DIR" > "$CONFIG_DIR/base_path.config"

# 3. Virtual Environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# 4. Install/Update Dependencies
echo "Installing/Updating Python dependencies..."
"$VENV_PATH/bin/pip" install --upgrade pip
"$VENV_PATH/bin/pip" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 5. MCP Configuration (Preserve if exists)
echo "Configuring MCP..."
MCP_CONFIG_PATH="$CONFIG_DIR/mcp_config.json"

if [ ! -f "$MCP_CONFIG_PATH" ]; then
    # Copy built-in servers if they exist in repo
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
    echo "Generated new MCP config at $MCP_CONFIG_PATH"
else
    echo "Preserving existing MCP config."
fi

# 6. Alias Setup
BASHRC="$HOME/.bashrc"
AI_RUN_SCRIPT="$REPO_DIR/ai_run.sh"
ALIAS_LINE="alias ai='$AI_RUN_SCRIPT'"

if grep -q "alias ai=" "$BASHRC"; then
    # Update existing alias if path changed
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
else
    echo -e "\n# AI Shortcut\n$ALIAS_LINE" >> "$BASHRC"
fi

# 7. Permission Fix
chmod +x "$AI_RUN_SCRIPT"
chmod +x "$REPO_DIR/uninstall.sh"
chmod +x "$REPO_DIR/install.sh"

echo -e "\n✅ Installation/Update Complete!"
echo "Current Version: $(cat $REPO_DIR/version.txt 2>/dev/null || echo 'unknown')"
echo "Please run: source ~/.bashrc"
