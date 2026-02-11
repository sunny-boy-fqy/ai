#!/bin/bash

# Update Private Configuration Script
# This script helps sync your PRIVATE configuration (keys, history) to a separate private repository.
# It does NOT touch the main AI tool repository.

CONFIG_DIR="$HOME/.config/ai"
URL_CONFIG="$CONFIG_DIR/repo_url.config"

echo "=== 🔒 Private Config Sync ==="

if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Config directory $CONFIG_DIR does not exist. Run 'ai new' first."
    exit 1
fi

cd "$CONFIG_DIR" || exit

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing private config repository..."
    git init
    echo ".python_venv/" >> .gitignore
    echo "__pycache__/" >> .gitignore
    echo "*.log" >> .gitignore
    git add .gitignore
    git commit -m "Initialize private config repo"
fi

# Check for remote URL
if [ ! -f "$URL_CONFIG" ]; then
    echo "No remote repository configured for backup."
    read -p "Enter private Git URL (e.g., git@github.com:user/private-ai-config.git): " REMOTE_URL
    if [ -z "$REMOTE_URL" ]; then
        echo "Skipping remote configuration."
    else
        echo "$REMOTE_URL" > "$URL_CONFIG"
        git remote add origin "$REMOTE_URL"
    fi
else
    REMOTE_URL=$(cat "$URL_CONFIG")
    if ! git remote | grep -q origin; then
        git remote add origin "$REMOTE_URL"
    fi
fi

# Sync
echo "Syncing configuration..."
git add .
git commit -m "Auto-update config: $(date)"

if [ -n "$REMOTE_URL" ]; then
    echo "Pushing to $REMOTE_URL..."
    git push -u origin main || git push -u origin master
fi

echo "✅ Configuration synced."