#!/bin/bash

# Go to your project directory
cd /Users/praneeththanniru/Projects/antigravity-agent

# Add all changes
git add .

# Commit changes with timestamp
git commit -m "Auto-update: $(date '+%Y-%m-%d %H:%M:%S')"

# Push to GitHub main branch
git push origin main
