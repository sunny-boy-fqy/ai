#!/bin/bash

# Script to update and push private configuration to a GitHub repository.

CONFIG_DIR="$HOME/.config/ai"
URL_CONFIG="$CONFIG_DIR/url.config"
REMOTE_REPO_URL="git@github.com:sunny-boy-fqy/ai-config.git" # Default for private config

# Ensure the configuration directory exists
mkdir -p "$CONFIG_DIR"

# Check if URL config file exists, if not, prompt user and save it
if [ ! -f "$URL_CONFIG" ]; then
    echo "Configuration URL not found."
    read -p "Enter the GitHub repository URL for your private config (e.g., git@github.com:user/repo.git or https://...): " user_url
    if [ -z "$user_url" ]; then
        echo "No URL provided. Using default: $REMOTE_REPO_URL"
        echo "$REMOTE_REPO_URL" > "$URL_CONFIG"
    else
        echo "$user_url" > "$URL_CONFIG"
        echo "Repository URL saved to $URL_CONFIG"
    fi
fi

# Read the URL from the config file
REPO_URL=$(cat "$URL_CONFIG")

# Ensure the config directory is a Git repository
if [ ! -d "$CONFIG_DIR/.git" ]; then
    echo "Initializing Git repository in $CONFIG_DIR..."
    cd "$CONFIG_DIR" || exit
    git init
    git config user.name "fangqiyu" # Setting identity for the config repo
    git config user.email "fangqiyu@example.com" # Setting identity for the config repo
    git add .
    git commit -m "Initial commit for private AI configuration"
    echo "Git repository initialized."
else
    cd "$CONFIG_DIR" || exit
fi

# Add remote origin if it doesn't exist
if ! git remote | grep -q origin; then
    echo "Adding remote origin: $REPO_URL"
    git remote add origin "$REPO_URL"
else
    # Optionally update remote if it exists but URL is different
    # For now, we assume the user wants to use the stored URL
    echo "Remote origin already exists. Using: $(git remote get-url origin)"
fi

# Add any new or modified files
git add .

# Commit changes
echo "Committing changes..."
git commit -m "Update private AI configuration"

# Push to the remote repository
echo "Pushing changes to $REPO_URL..."
git push origin main # Assuming the default branch is master, might need to adjust if it's main
echo "Push complete."

