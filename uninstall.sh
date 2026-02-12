#!/bin/bash

# AI Tool Deep Uninstallation Script (Linux)

CONFIG_DIR="$HOME/.config/ai"
USER_AI_DIR="$HOME/.ai"
BASHRC="$HOME/.bashrc"

# 1. Self-cloning logic
if [[ "$0" != "/tmp/"* ]]; then
    TMP_DIR="/tmp/ai_cleanup_$(date +%s)"
    mkdir -p "$TMP_DIR"
    cp "$0" "$TMP_DIR/uninstall.sh"
    chmod +x "$TMP_DIR/uninstall.sh"
    echo "⏳ Moving to temporary environment for deep cleanup..."
    exec "$TMP_DIR/uninstall.sh" "$@"
    exit
fi

echo "=== 🗑️ AI CLI Deep Uninstallation ==="

# 2. Kill processes
echo "🛑 Stopping AI processes..."
pkill -9 -f "ai_caller.py" 2>/dev/null
pkill -9 -f "ai_run.sh" 2>/dev/null
pkill -9 -f "\.config/ai/node" 2>/dev/null

# 3. Resolve TARGET_DIR
if [ -f "$CONFIG_DIR/base_path.config" ]; then
    TARGET_DIR=$(cat "$CONFIG_DIR/base_path.config")
else
    TARGET_DIR="$HOME/ai"
fi

# 4. Remove Files
echo "📁 Deleting folders..."
rm -rf "$CONFIG_DIR"
rm -rf "$USER_AI_DIR"
rm -rf "$TARGET_DIR"

# 5. Clean PATH/Alias
echo "🔗 Cleaning .bashrc..."
sed -i '/# AI Shortcut/d' "$BASHRC" 2>/dev/null
sed -i "/alias ai='.*ai_run.sh'/d" "$BASHRC" 2>/dev/null

echo -e "\n✅ Uninstallation complete. Please run: source ~/.bashrc"
