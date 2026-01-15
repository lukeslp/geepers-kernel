#!/usr/bin/env bash
# Install MCP Server for Claude Code / Cursor
#
# This script sets up the Shared Library MCP server for use with AI coding assistants.
#
# Author: Luke Steuber
# Date: 2025-11-20

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════╗"
echo "║  Shared Library MCP Server Installation          ║"
echo "╚════════════════════════════════════════════════════╝"
echo

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
    CURSOR_CONFIG_DIR="$HOME/Library/Application Support/Cursor/User/globalStorage"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
    CURSOR_CONFIG_DIR="$HOME/.config/Cursor/User/globalStorage"
else
    OS="Windows"
    CLAUDE_CONFIG_DIR="$APPDATA/Claude"
    CURSOR_CONFIG_DIR="$APPDATA/Cursor/User/globalStorage"
fi

echo "✓ Detected OS: $OS"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Error: python3 not found"
    echo "  Please install Python 3.8+ and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python version: $PYTHON_VERSION"
echo

# Install shared library
echo "📦 Installing shared library..."
cd /home/coolhand/shared
pip install -e . > /dev/null 2>&1
echo "✓ Shared library installed"
echo

# Make stdio server executable
echo "🔧 Configuring MCP server..."
chmod +x /home/coolhand/shared/mcp/stdio_server.py
echo "✓ stdio_server.py is executable"
echo

# Setup Claude Code
echo "🤖 Setting up Claude Code integration..."
if [[ -d "$CLAUDE_CONFIG_DIR" ]]; then
    mkdir -p "$CLAUDE_CONFIG_DIR"
    
    CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
    
    if [[ -f "$CONFIG_FILE" ]]; then
        echo "⚠  Config file already exists: $CONFIG_FILE"
        echo "   Backing up to $CONFIG_FILE.backup"
        cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
    fi
    
    cp /home/coolhand/shared/mcp/claude_code_config.json "$CONFIG_FILE"
    echo "✓ Claude Code config installed"
    echo "  Location: $CONFIG_FILE"
else
    echo "ℹ  Claude Code not detected (no config directory)"
    echo "  You can manually copy claude_code_config.json later"
fi
echo

# Setup Cursor
echo "📝 Setting up Cursor integration..."
if [[ -d "$CURSOR_CONFIG_DIR" ]]; then
    CURSOR_CONFIG_FILE="$CURSOR_CONFIG_DIR/config.json"
    
    if [[ ! -f "$CURSOR_CONFIG_FILE" ]]; then
        # Create new config
        cp /home/coolhand/shared/mcp/claude_code_config.json "$CURSOR_CONFIG_FILE"
        echo "✓ Cursor config installed"
        echo "  Location: $CURSOR_CONFIG_FILE"
    else
        echo "ℹ  Cursor config already exists"
        echo "  Please manually merge with: /home/coolhand/shared/mcp/claude_code_config.json"
    fi
else
    echo "ℹ  Cursor not detected (no config directory)"
    echo "  You can manually copy config later"
fi
echo

# Check API keys
echo "🔑 Checking API keys..."
API_KEYS=(
    "ANTHROPIC_API_KEY"
    "OPENAI_API_KEY"
    "XAI_API_KEY"
    "MISTRAL_API_KEY"
    "COHERE_API_KEY"
)

KEYS_FOUND=0
for KEY in "${API_KEYS[@]}"; do
    if [[ -n "${!KEY}" ]]; then
        echo "  ✓ $KEY is set"
        ((KEYS_FOUND++))
    else
        echo "  ✗ $KEY not set"
    fi
done

echo
if [[ $KEYS_FOUND -eq 0 ]]; then
    echo "⚠  Warning: No API keys found in environment"
    echo "  Please set API keys in your shell profile (~/.bashrc or ~/.zshrc)"
    echo "  Example:"
    echo "    export ANTHROPIC_API_KEY=\"your-key\""
    echo "    export OPENAI_API_KEY=\"your-key\""
else
    echo "✓ Found $KEYS_FOUND API key(s)"
fi
echo

# Test server
echo "🧪 Testing MCP server..."
if python3 /home/coolhand/shared/mcp/stdio_server.py <<< '{"jsonrpc":"2.0","id":1,"method":"ping"}' 2>/dev/null | grep -q "ok"; then
    echo "✓ MCP server responding correctly"
else
    echo "⚠  Warning: MCP server test failed"
    echo "  Server may still work - check logs if issues occur"
fi
echo

# Print next steps
echo "╔════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                          ║"
echo "╚════════════════════════════════════════════════════╝"
echo
echo "Next Steps:"
echo
echo "1. Set API keys (if not already done):"
echo "   Add to ~/.bashrc or ~/.zshrc:"
echo "     export ANTHROPIC_API_KEY=\"your-key\""
echo "     export OPENAI_API_KEY=\"your-key\""
echo "   Then: source ~/.bashrc"
echo
echo "2. Restart your AI assistant:"
echo "   - Claude Code: Quit and restart completely"
echo "   - Cursor: Quit and restart completely"
echo
echo "3. Verify connection:"
echo "   Ask: \"List available MCP tools\""
echo "   You should see 31+ tools"
echo
echo "4. Try a test:"
echo "   Ask: \"Use cache_set to store 'hello' with key 'test'\""
echo
echo "Documentation:"
echo "  - Claude Code: /home/coolhand/shared/mcp/CLAUDE_CODE_SETUP.md"
echo "  - Cursor:      /home/coolhand/shared/mcp/CURSOR_INTEGRATION.md"
echo "  - Tool List:   /home/coolhand/shared/mcp/TOOL_AUDIT.md"
echo
echo "Troubleshooting:"
echo "  Check logs: python3 /home/coolhand/shared/mcp/stdio_server.py 2> /tmp/mcp.log"
echo
echo "Happy coding with 31+ MCP tools! 🚀"
