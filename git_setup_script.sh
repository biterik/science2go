#!/bin/bash
# Science2Go Git Setup Script
# Sets up version control for https://github.com/biterik/science2go

set -e  # Exit on any error

echo "🚀 Setting up Git for Science2Go project"
echo "Repository: https://github.com/biterik/science2go"
echo "============================================="

# Check if we're in a git repository
if [ -d ".git" ]; then
    echo "⚠️  Git repository already exists."
    read -p "Do you want to reinitialize? This will preserve your history. [y/N]: " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted by user"
        exit 1
    fi
else
    echo "📁 Initializing new Git repository..."
    git init
fi

# Set up the remote repository
REPO_URL="https://github.com/biterik/science2go.git"
echo "🔗 Setting up remote repository..."

# Remove existing origin if it exists
if git remote | grep -q origin; then
    echo "   Removing existing origin..."
    git remote remove origin
fi

# Add the correct origin
git remote add origin $REPO_URL
echo "   ✅ Added remote origin: $REPO_URL"

# Set up main branch (modern Git uses 'main' instead of 'master')
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "🌿 Setting up main branch..."
    if [ -n "$CURRENT_BRANCH" ]; then
        git branch -M main
        echo "   ✅ Renamed '$CURRENT_BRANCH' to 'main'"
    else
        git checkout -b main
        echo "   ✅ Created 'main' branch"
    fi
fi

# Configure Git settings (if not already set globally)
echo "⚙️  Checking Git configuration..."

if [ -z "$(git config user.name)" ]; then
    echo "   Git user.name not set."
    read -p "   Enter your full name: " GIT_NAME
    git config user.name "$GIT_NAME"
    echo "   ✅ Set user.name: $GIT_NAME"
fi

if [ -z "$(git config user.email)" ]; then
    echo "   Git user.email not set."
    read -p "   Enter your email: " GIT_EMAIL
    git config user.email "$GIT_EMAIL"
    echo "   ✅ Set user.email: $GIT_EMAIL"
fi

# Set up useful Git configurations for this project
echo "🔧 Configuring project-specific Git settings..."

# Ignore file mode changes (useful for cross-platform development)
git config core.filemode false
echo "   ✅ Disabled file mode tracking"

# Set line ending handling
git config core.autocrlf input
echo "   ✅ Set line ending handling"

# Set default push behavior
git config push.default current
echo "   ✅ Set push behavior to 'current'"

# Add helpful aliases
git config alias.st status
git config alias.co checkout
git config alias.br branch
git config alias.unstage 'reset HEAD --'
git config alias.last 'log -1 HEAD'
echo "   ✅ Added helpful Git aliases"

# Stage all files
echo "📦 Staging files for initial commit..."

# Add .gitignore first
git add .gitignore
echo "   ✅ Added .gitignore"

# Add all project files
git add .
echo "   ✅ Staged all project files"

# Show what will be committed
echo ""
echo "📋 Files to be committed:"
git status --short | head -20
if [ $(git status --short | wc -l) -gt 20 ]; then
    echo "   ... and $(( $(git status --short | wc -l) - 20 )) more files"
fi

echo ""
read -p "💾 Proceed with initial commit? [Y/n]: " -r
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo "❌ Commit cancelled. Files are staged and ready."
    exit 0
fi

# Create initial commit
echo "📝 Creating initial commit..."
git commit -m "Initial commit: Science2Go project setup

- Academic paper to podcast converter
- GUI application with 4-tab interface
- PDF metadata extraction
- AI-powered text processing
- Audio generation capabilities
- Cross-platform compatibility

Project structure:
- src/: Main application code
- output/: Generated files and user data
- Configuration and requirements included"

echo "   ✅ Created initial commit"

# Check if remote repository exists and push
echo "🔄 Pushing to GitHub..."
echo "   Checking remote repository..."

# Try to fetch from remote to see if it exists
if git ls-remote origin &> /dev/null; then
    echo "   Remote repository exists"
    
    # Try to pull any existing content
    if git pull origin main --allow-unrelated-histories &> /dev/null; then
        echo "   ✅ Merged with existing remote content"
    else
        echo "   No existing content to merge"
    fi
    
    # Push our changes
    git push -u origin main
    echo "   ✅ Pushed to origin/main"
else
    echo "   ⚠️  Remote repository not found or not accessible"
    echo "   Make sure you:"
    echo "     1. Created the repository at https://github.com/biterik/science2go"
    echo "     2. Have push access to the repository"
    echo "     3. Are authenticated with GitHub (SSH keys or token)"
    echo ""
    echo "   To push later, run: git push -u origin main"
fi

# Final instructions
echo ""
echo "🎉 Git setup completed!"
echo "============================================="
echo "Repository: https://github.com/biterik/science2go"
echo "Branch: main"
echo "Files staged and committed: $(git ls-files | wc -l) files"
echo ""
echo "📚 Next steps:"
echo "1. Visit https://github.com/biterik/science2go to view your repository"
echo "2. Continue development with: git add, git commit, git push"
echo "3. Use 'git status' to check your working directory"
echo "4. Use 'git log --oneline' to view commit history"
echo ""
echo "🔄 Useful commands:"
echo "   git status          # Check current status"
echo "   git add .           # Stage all changes"
echo "   git commit -m 'msg' # Commit with message"
echo "   git push            # Push to GitHub"
echo "   git pull            # Pull latest changes"
echo ""
echo "✅ Science2Go is now under version control!"