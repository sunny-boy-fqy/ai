#!/bin/bash

# AI Tool Installation & Deployment Script

GITHUB_REPO="git@github.com:sunny-boy-fqy/ai.git"
CONFIG_DIR="$HOME/.config/ai"

echo "=== 🤖 AI Tool Deployment ==="

# 1. Select Installation Directory
read -p "Enter installation directory [default: $HOME/ai]: " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-$HOME/ai}

# Expand ~ if used
INSTALL_DIR="${INSTALL_DIR/#\~/$HOME}"

# 2. Clone or Sync Repository
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing repository at $INSTALL_DIR..."
    cd "$INSTALL_DIR" && git pull origin main
else
    echo "Cloning tool to $INSTALL_DIR..."
    git clone "$GITHUB_REPO" "$INSTALL_DIR"
    cd "$INSTALL_DIR" || exit
fi

# 3. Setup Configuration Directory
echo "Ensuring config directory exists: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# 4. Create base_path.config
echo "Configuring base path..."
echo "$INSTALL_DIR" > "$CONFIG_DIR/base_path.config"

# 5. Setup Python Virtual Environment
VENV_PATH="$CONFIG_DIR/python_venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment in $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
fi

# 6. Install/Update Dependencies
echo "Installing dependencies..."
"$VENV_PATH/bin/pip" install --upgrade pip
if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    "$VENV_PATH/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    "$VENV_PATH/bin/pip" install openai zhipuai groq beautifulsoup4 ebooklib httpx PyJWT tqdm pydantic lxml requests
fi

# 7. Setup .bashrc Alias
BASHRC="$HOME/.bashrc"
AI_RUN_SCRIPT="$INSTALL_DIR/ai_run.sh"
ALIAS_LINE="alias ai='$AI_RUN_SCRIPT'"

if grep -q "alias ai=" "$BASHRC"; then
    sed -i "s|alias ai=.*|$ALIAS_LINE|" "$BASHRC"
    echo "Updated 'ai' alias in .bashrc"
else
    echo -e "
# AI Shortcut
$ALIAS_LINE" >> "$BASHRC"
    echo "Added 'ai' alias to .bashrc"
fi

echo -e "
✅ Deployment Successful!"
echo "Please run: source ~/.bashrc"
echo "Then use 'ai' to start."
