#!/bin/bash

# Go to your project directory
cd /Users/praneeththanniru/Projects/antigravity-agent

# Check if there are changes
if [[ -n $(git status -s) ]]; then
    # Add all changes
    git add .

    # Commit with timestamp
    git commit -m "Auto-update: $(date '+%Y-%m-%d %H:%M:%S')"

    # Push to GitHub
    git push origin main

    echo "Changes pushed successfully at $(date '+%Y-%m-%d %H:%M:%S')"
else
    echo "No changes to commit at $(date '+%Y-%m-%d %H:%M:%S')"
fi
