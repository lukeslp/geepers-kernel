#!/bin/bash
# Dreamwalker MCP - Cursor Installation Script
# 
# This script helps you configure Cursor to connect to the remote Dreamwalker MCP server.
# Run this on your LOCAL machine (not the server).

set -e

echo "🌊 Dreamwalker MCP - Cursor Setup"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Copy bridge script to local machine
echo "Step 1: Setting up MCP bridge..."
SCRIPT_DIR="$HOME/.dreamwalker"
mkdir -p "$SCRIPT_DIR"

# Download bridge script from server
echo "Downloading mcp_http_bridge.py from server..."
scp coolhand@dr.eamer.dev:/home/coolhand/shared/mcp/mcp_http_bridge.py "$SCRIPT_DIR/" || {
    echo -e "${RED}Error: Could not download bridge script${NC}"
    echo "Manual download:"
    echo "  scp coolhand@dr.eamer.dev:/home/coolhand/shared/mcp/mcp_http_bridge.py ~/.dreamwalker/"
    exit 1
}

chmod +x "$SCRIPT_DIR/mcp_http_bridge.py"
echo -e "${GREEN}✓${NC} Bridge script installed at $SCRIPT_DIR/mcp_http_bridge.py"

# Step 2: Determine Cursor config location
echo ""
echo "Step 2: Configuring Cursor..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CURSOR_CONFIG_DIR="$HOME/Library/Application Support/Cursor/User"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    CURSOR_CONFIG_DIR="$HOME/.config/Cursor/User"
else
    # Windows (via WSL or Git Bash)
    CURSOR_CONFIG_DIR="$APPDATA/Cursor/User"
fi

mkdir -p "$CURSOR_CONFIG_DIR"
CURSOR_SETTINGS="$CURSOR_CONFIG_DIR/settings.json"

# Step 3: Create or update Cursor settings
echo "Cursor config location: $CURSOR_SETTINGS"

if [ -f "$CURSOR_SETTINGS" ]; then
    echo -e "${YELLOW}⚠${NC} settings.json already exists"
    echo "You'll need to manually add the mcpServers section."
    echo ""
    echo "Add this to your settings.json:"
    cat << EOF
{
  "mcpServers": {
    "dreamwalker": {
      "command": "python3",
      "args": [
        "$SCRIPT_DIR/mcp_http_bridge.py",
        "--url",
        "https://dr.eamer.dev/mcp"
      ]
    }
  }
}
EOF
else
    # Create new settings.json
    cat > "$CURSOR_SETTINGS" << EOF
{
  "mcpServers": {
    "dreamwalker": {
      "command": "python3",
      "args": [
        "$SCRIPT_DIR/mcp_http_bridge.py",
        "--url",
        "https://dr.eamer.dev/mcp"
      ]
    }
  }
}
EOF
    echo -e "${GREEN}✓${NC} Created new settings.json with Dreamwalker MCP config"
fi

# Step 4: Test the bridge
echo ""
echo "Step 3: Testing bridge connection..."

if command -v python3 &> /dev/null; then
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
        python3 "$SCRIPT_DIR/mcp_http_bridge.py" --url https://dr.eamer.dev/mcp 2>/dev/null | \
        head -1 | jq -r '.result.tools | length' > /tmp/tool_count.txt 2>/dev/null || echo "0" > /tmp/tool_count.txt
    
    TOOL_COUNT=$(cat /tmp/tool_count.txt)
    if [ "$TOOL_COUNT" -gt "20" ]; then
        echo -e "${GREEN}✓${NC} Bridge is working! Found $TOOL_COUNT tools"
    else
        echo -e "${YELLOW}⚠${NC} Bridge test inconclusive (found $TOOL_COUNT tools)"
    fi
else
    echo -e "${YELLOW}⚠${NC} python3 not found, skipping bridge test"
fi

# Final instructions
echo ""
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Restart Cursor"
echo "2. Check MCP status in Cursor (look for 'dreamwalker' server)"
echo "3. Test: Ask Cursor to 'Search arXiv for papers about AI'"
echo ""
echo "Troubleshooting:"
echo "  View Cursor MCP logs in Cursor settings"
echo "  Test bridge: python3 $SCRIPT_DIR/mcp_http_bridge.py --url https://dr.eamer.dev/mcp"
echo "  Check server: curl https://dr.eamer.dev/mcp/health"
echo ""
echo "Documentation: /home/coolhand/shared/mcp/INDEX.md"
echo ""

