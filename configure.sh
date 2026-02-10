#!/bin/bash

# Get the absolute path of the directory where this script is located
AI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="$HOME/.config/ai"

# Ensure config directory exists
mkdir -p "$CONFIG_DIR"

# 1. Update base_path.config
echo "$AI_DIR" > "$CONFIG_DIR/base_path.config"
echo "Updated $CONFIG_DIR/base_path.config with: $AI_DIR"

# 2. Update .bashrc alias
BASHRC="$HOME/.bashrc"
AI_ALIAS="alias ai='$AI_DIR/ai_run.sh'"

# Check if alias exists and update or add it
if grep -q "alias ai=" "$BASHRC"; then
    # Update existing alias
    sed -i "s|alias ai=.*|${AI_ALIAS}|" "$BASHRC"
    echo "Updated 'ai' alias in .bashrc"
else
    # Add new alias
    echo -e "\n# AI Shortcut\n${AI_ALIAS}" >> "$BASHRC"
    echo "Added 'ai' alias to .bashrc"
fi

echo "Configuration complete. Please run 'source ~/.bashrc' to apply changes."
