#!/bin/bash

# Script to update and push the AI tool code to GitHub.

AI_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REMOTE_URL="git@github.com:sunny-boy-fqy/ai.git"

cd "$AI_DIR" || exit

# Ensure remote is correct
if ! git remote | grep -q origin; then
    git remote add origin "$REMOTE_URL"
else
    git remote set-url origin "$REMOTE_URL"
fi

# Add changes
git add .

# Prompt for commit message
read -p "Enter commit message (default: 'Update AI tool'): " commit_msg
if [ -z "$commit_msg" ]; then
    commit_msg="Update AI tool"
fi

# Commit
git commit -m "$commit_msg"

# Push to main
echo "Pushing tool updates to GitHub (main branch)..."
git push origin main

echo "Tool update complete."
