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

# 3. Remove Code
CONFIG_DIR="$HOME/.config/ai"
if [ -f "$CONFIG_DIR/base_path.config" ]; then
    ACTUAL_TARGET_DIR=$(cat "$CONFIG_DIR/base_path.config")
else
    ACTUAL_TARGET_DIR="$HOME/.ai"
fi

read -p "Do you want to remove the AI tool source code directory ($ACTUAL_TARGET_DIR)? (y/n): " remove_code
if [[ "$remove_code" =~ ^[Yy]$ ]]; then
    echo "Removing source code..."
    rm -rf "$ACTUAL_TARGET_DIR"
    echo "Source code removed."
fi

echo -e "
✅ Uninstallation Complete!"
echo "Please run: source ~/.bashrc"
