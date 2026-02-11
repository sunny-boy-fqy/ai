#!/bin/bash

# AI Tool Uninstallation Script

CONFIG_DIR="$HOME/.config/ai"
USER_AI_DIR="$HOME/.ai"
BASHRC="$HOME/.bashrc"

echo "=== 🗑️  AI CLI Uninstallation ==="

# 1. Remove Alias
echo "Removing alias from .bashrc..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' '/# AI Shortcut/d' "$BASHRC"
    sed -i '' "/alias ai='.*ai_run.sh'/d" "$BASHRC"
else
    sed -i '/# AI Shortcut/d' "$BASHRC"
    sed -i "/alias ai='.*ai_run.sh'/d" "$BASHRC"
fi

# 2. Optional: Remove Configuration
read -p "Do you want to keep your configuration and API keys? (y/n): " keep_config

if [[ "$keep_config" =~ ^[Nn]$ ]]; then
    echo "Removing configuration and data..."
    rm -rf "$CONFIG_DIR"
    rm -rf "$USER_AI_DIR"
    echo "Configuration removed."
else
    echo "Configuration preserved in $CONFIG_DIR"
fi

echo -e "
✅ Uninstallation Complete!"
echo "Please run: source ~/.bashrc"
