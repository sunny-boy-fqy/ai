#!/bin/bash

# AI Tool Installation Script

REPO_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="$HOME/.config/ai"
USER_AI_DIR="$HOME/.ai"
MCP_SERVERS_DIR="$USER_AI_DIR/mcp_servers"
VENV_PATH="$CONFIG_DIR/python_venv"

echo "=== 🤖 AI CLI Installation ==="

# 1. Directory Setup
echo "Creating directories..."
mkdir -p "$CONFIG_DIR"
mkdir -p "$MCP_SERVERS_DIR"

# 2. Base Path Config
echo "$REPO_DIR" > "$CONFIG_DIR/base_path.config"

# 3. Virtual Environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
fi

# 4. Install Dependencies
echo "Installing Python dependencies..."
# Update pip first
"$VENV_PATH/bin/pip" install --upgrade pip
# Install required packages
"$VENV_PATH/bin/pip" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests mcp ddgs duckduckgo_search

# 5. MCP Configuration
echo "Configuring MCP..."

# Copy built-in servers to user directory if they don't exist
if [ -f "$REPO_DIR/mcp_servers/web_search_server.py" ]; then
    cp "$REPO_DIR/mcp_servers/web_search_server.py" "$MCP_SERVERS_DIR/"
fi
# Note: Since we moved files in the previous step manually, this might fail if the repo is clean.
# But for a fresh install from git, the files would be in the repo.
# For now, let's assume the user has the repo.

# Generate mcp_config.json
MCP_CONFIG_PATH="$CONFIG_DIR/mcp_config.json"
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
echo "Generated MCP config at $MCP_CONFIG_PATH"

# 6. Alias Setup
BASHRC="$HOME/.bashrc"
AI_RUN_SCRIPT="$REPO_DIR/ai_run.sh"
ALIAS_LINE="alias ai='$AI_RUN_SCRIPT'"

if grep -q "alias ai=" "$BASHRC"; then
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
else
    echo -e "\n# AI Shortcut\n$ALIAS_LINE" >> "$BASHRC"
fi

# 7. Permission Fix
chmod +x "$AI_RUN_SCRIPT"

echo -e "\n✅ Installation Complete!"
echo "Please run: source ~/.bashrc"
echo "Usage: ai 'help'"