#!/bin/bash
# Setup script to install git hooks

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.githooks"
GIT_HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "📦 Setting up git hooks..."

# Make hooks executable
chmod +x "$HOOKS_DIR"/*

# Create symlinks in .git/hooks
for hook in "$HOOKS_DIR"/*; do
    hook_name=$(basename "$hook")
    
    # Skip this setup script
    if [ "$hook_name" = "setup-hooks.sh" ]; then
        continue
    fi
    
    target="$GIT_HOOKS_DIR/$hook_name"
    
    # Remove existing hook if it's a symlink
    if [ -L "$target" ]; then
        rm "$target"
    fi
    
    # Create symlink
    ln -s "$hook" "$target"
    echo "✅ Installed $hook_name hook"
done

echo "🎉 Git hooks setup complete!"
echo ""
echo "Available hooks:"
echo "  - pre-push: Builds documentation before pushing"
echo ""
echo "To disable a hook temporarily, use: git push --no-verify"
