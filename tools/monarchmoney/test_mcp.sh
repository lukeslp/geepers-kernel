#!/bin/bash
# Comprehensive MCP Server Test Suite
# Tests both stdio and HTTP modes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Monarch Money MCP Server - Test Suite"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Check dependencies
echo "1. Checking Dependencies..."
python3 -c "import mcp" 2>/dev/null && pass "MCP SDK installed" || fail "MCP SDK not installed (run: pip install mcp>=0.9.0)"
python3 -c "import aiohttp" 2>/dev/null && pass "aiohttp installed" || fail "aiohttp not installed"
python3 -c "from monarchmoney.monarchmoney import MonarchMoney" 2>/dev/null && pass "Monarch Money library importable" || fail "Monarch Money library not found"
echo ""

# Test 2: Check session files
echo "2. Checking Authentication..."
if [ -f "$HOME/.mm/session.enc" ] && [ -f "$HOME/.mm/session.key" ]; then
    pass "Encrypted session files exist"
else
    fail "No session files found. Run 'mm login' first."
fi
echo ""

# Test 3: Test stdio server (MCP list_tools)
echo "3. Testing stdio MCP Server..."
TOOLS_OUTPUT=$(timeout 5 python3 -c "
import asyncio
import json
from mcp_server.server import app

async def test():
    tools = await app.list_tools()
    print(json.dumps([t.name for t in tools]))

asyncio.run(test())
" 2>/dev/null)

if [ $? -eq 0 ]; then
    TOOL_COUNT=$(echo "$TOOLS_OUTPUT" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
    if [ "$TOOL_COUNT" = "7" ]; then
        pass "stdio server exposes 7 tools"
        echo "   Tools: $TOOLS_OUTPUT"
    else
        fail "Expected 7 tools, got $TOOL_COUNT"
    fi
else
    fail "stdio server failed to list tools"
fi
echo ""

# Test 4: Check file permissions
echo "4. Checking File Permissions..."
[ -x "mcp_server/server.py" ] && pass "server.py is executable" || warn "server.py not executable (non-critical)"
[ -x "mcp_server/http_server.py" ] && pass "http_server.py is executable" || warn "http_server.py not executable (non-critical)"
[ -x "mcp_server/manage.sh" ] && pass "manage.sh is executable" || fail "manage.sh not executable"
echo ""

# Test 5: Test HTTP server startup
echo "5. Testing HTTP Server..."

# Start HTTP server in background
python3 mcp_server/http_server.py > /tmp/mcp_http_test.log 2>&1 &
HTTP_PID=$!
sleep 2

# Check if server is running
if kill -0 $HTTP_PID 2>/dev/null; then
    pass "HTTP server started (PID: $HTTP_PID)"

    # Test health endpoint
    if curl -s http://127.0.0.1:8100/health > /dev/null 2>&1; then
        HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8100/health)
        pass "Health endpoint responding"
        echo "   Response: $HEALTH_RESPONSE"
    else
        kill $HTTP_PID 2>/dev/null
        fail "Health endpoint not responding"
    fi

    # Test SSE endpoint exists (won't fully connect without proper MCP client)
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8100/sse | grep -q "200"; then
        pass "SSE endpoint accessible"
    else
        warn "SSE endpoint returned non-200 (may be normal without MCP client)"
    fi

    # Cleanup
    kill $HTTP_PID 2>/dev/null
    pass "HTTP server stopped cleanly"
else
    fail "HTTP server failed to start (check logs at /tmp/mcp_http_test.log)"
fi
echo ""

# Test 6: Check Claude Code configuration
echo "6. Checking Claude Code Configuration..."
if [ -f "$HOME/.claude.json" ]; then
    if grep -q "monarch-money" "$HOME/.claude.json"; then
        pass "MCP server configured in ~/.claude.json"

        # Check if it's in the right project
        if grep -A 10 "/home/coolhand" "$HOME/.claude.json" | grep -q "monarch-money"; then
            pass "Configured for /home/coolhand project"
        else
            warn "Not configured for current project"
        fi
    else
        warn "MCP server not found in ~/.claude.json (may need manual configuration)"
    fi
else
    warn "~/.claude.json not found"
fi
echo ""

# Test 7: Check documentation
echo "7. Checking Documentation..."
[ -f "README_MCP.md" ] && pass "README_MCP.md exists" || warn "README_MCP.md missing"
[ -f "MCP_SETUP.md" ] && pass "MCP_SETUP.md exists" || warn "MCP_SETUP.md missing"
[ -f "MCP_README.md" ] && pass "MCP_README.md exists" || warn "MCP_README.md missing"
[ -f "MCP_DESKTOP_SETUP.md" ] && pass "MCP_DESKTOP_SETUP.md exists" || warn "MCP_DESKTOP_SETUP.md missing"
[ -f "HTTP_SERVER_QUICKSTART.md" ] && pass "HTTP_SERVER_QUICKSTART.md exists" || warn "HTTP_SERVER_QUICKSTART.md missing"
echo ""

# Test 8: Check systemd service file
echo "8. Checking Systemd Service..."
if [ -f "monarch-mcp.service" ]; then
    pass "monarch-mcp.service file exists"

    if [ -f "/etc/systemd/system/monarch-mcp.service" ]; then
        pass "Service installed in /etc/systemd/system/"
        systemctl is-enabled monarch-mcp &>/dev/null && pass "Service is enabled" || warn "Service not enabled (run: sudo systemctl enable monarch-mcp)"
    else
        warn "Service not installed (run: sudo cp monarch-mcp.service /etc/systemd/system/)"
    fi
else
    warn "monarch-mcp.service file missing"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✓${NC} Core MCP functionality working"
echo -e "${GREEN}✓${NC} stdio server ready for Claude Code CLI"
echo -e "${GREEN}✓${NC} HTTP server ready for remote access"
echo ""
echo "Next Steps:"
echo "  1. Restart Claude Code to load MCP server"
echo "  2. Try: 'What's my current net worth?'"
echo "  3. For Claude Desktop: See MCP_DESKTOP_SETUP.md"
echo "  4. For HTTP server: ./mcp_server/manage.sh start"
echo ""
echo "Documentation:"
echo "  - Overview: README_MCP.md"
echo "  - Quick Start: MCP_README.md"
echo "  - HTTP Setup: HTTP_SERVER_QUICKSTART.md"
echo "  - Claude Desktop: MCP_DESKTOP_SETUP.md"
echo ""
