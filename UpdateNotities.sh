#!/bin/bash
# git_sync.sh
# Script to sync git repository with automatic pull, add, commit, and push

# Repository path
REPO_PATH="/Users/mikebos/Library/Mobile Documents/27N4MQEA55~pro~writer/Documents"

# Function to handle errors
handle_error() {
    echo "ERROR: $1"
    exit 1
}

# Change to repository directory
cd "$REPO_PATH" || handle_error "Could not change to repository directory at $REPO_PATH"

# Pull latest changes
git pull
if [ $? -ne 0 ]; then
    handle_error "Failed to pull latest changes. Please resolve conflicts manually."
fi

# Add all new files and directories
git add --all
if [ $? -ne 0 ]; then
    handle_error "Failed to add new files and directories."
fi

# Check if there are changes to commit
if git diff-index --quiet HEAD --; then
    echo "No changes to commit."
    exit 0
fi

# Commit changes with timestamp
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
git commit -m "Automatic sync: $TIMESTAMP"
if [ $? -ne 0 ]; then
    handle_error "Failed to commit changes."
fi

# Push changes to remote
git push
if [ $? -ne 0 ]; then
    handle_error "Failed to push changes to remote repository."
fi

echo "SUCCESS: Repository successfully synchronized."
exit 0