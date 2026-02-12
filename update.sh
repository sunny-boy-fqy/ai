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

# Prompt for branch
read -p "Enter target branch (default: 'dev'): " target_branch
if [ -z "$target_branch" ]; then
    target_branch="dev"
fi

# Commit
git commit -m "$commit_msg"

# Push
echo "Pushing tool updates to GitHub ($target_branch branch)..."
git push origin "$target_branch"

echo "Tool update complete."
