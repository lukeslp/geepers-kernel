#!/bin/bash
# Dependency Audit Quick Fix Script
# Generated: 2025-11-20
# For: /home/coolhand/shared/
#
# This script addresses CRITICAL dependency issues found in audit report.
# Review DEPENDENCY_AUDIT_REPORT.md for full details.

set -e  # Exit on error

echo "=========================================="
echo "Shared Library Dependency Quick Fixes"
echo "=========================================="
echo ""

# Backup current state
echo "1. Creating backup..."
cd /home/coolhand/shared
cp requirements.txt requirements.txt.backup-$(date +%Y%m%d_%H%M%S)
echo "   ✓ Backup created"
echo ""

# Fix critical version conflicts
echo "2. Fixing critical version conflicts..."
echo "   - Upgrading openai (beltalawda requires >=1.6.0, installed 1.3.7)"
pip install --upgrade "openai>=1.6.0,<3.0" --quiet
echo "   ✓ openai upgraded"

echo "   - Upgrading alembic (beltalawda requires >=1.13.0)"
pip install --upgrade "alembic>=1.13.0" --quiet
echo "   ✓ alembic upgraded"

echo "   - Upgrading httpx (mistralai requires >=0.28.1)"
pip install --upgrade "httpx>=0.28.1" --quiet
echo "   ✓ httpx upgraded"
echo ""

# Pin security-critical packages
echo "3. Pinning security-critical packages..."
echo "   - Pinning requests to >=2.32.5 (CVE-2024-47081, CVE-2024-35195)"
pip install --upgrade "requests>=2.32.5" --quiet
echo "   ✓ requests pinned"
echo ""

# Clean duplicate installations
echo "4. Cleaning duplicate installations..."
echo "   This may show 'Not found' errors - that's OK"
pip uninstall anthropic -y 2>/dev/null || true
pip uninstall anthropic -y 2>/dev/null || true
pip uninstall requests -y 2>/dev/null || true
pip uninstall requests -y 2>/dev/null || true
pip uninstall pillow -y 2>/dev/null || true
pip uninstall pillow -y 2>/dev/null || true
echo "   ✓ Duplicates removed"
echo ""

# Reinstall fresh
echo "5. Reinstalling clean versions..."
pip install "anthropic>=0.71.0" --quiet
pip install "requests>=2.32.5" --quiet
pip install "pillow>=11.0.0" --quiet
echo "   ✓ Clean versions installed"
echo ""

# Verify installations
echo "6. Verifying installations..."
python3 << 'PYEOF'
import sys

packages = {
    'openai': '1.6.0',
    'requests': '2.32.5',
    'anthropic': '0.71.0',
    'pillow': '11.0.0',
    'alembic': '1.13.0',
    'httpx': '0.28.1'
}

errors = []
for pkg, min_ver in packages.items():
    try:
        if pkg == 'pillow':
            from PIL import __version__ as pil_ver
            actual_ver = pil_ver
            pkg_name = 'PIL (Pillow)'
        else:
            mod = __import__(pkg)
            actual_ver = mod.__version__
            pkg_name = pkg

        print(f"   ✓ {pkg_name}: {actual_ver}")

        # Basic version comparison (assumes semantic versioning)
        actual_parts = [int(x) for x in actual_ver.split('.')[:3] if x.isdigit()]
        min_parts = [int(x) for x in min_ver.split('.')[:3]]

        if actual_parts < min_parts:
            errors.append(f"{pkg_name} version {actual_ver} is below minimum {min_ver}")
    except Exception as e:
        errors.append(f"Could not verify {pkg}: {e}")

if errors:
    print("\n   ⚠ WARNINGS:")
    for err in errors:
        print(f"     - {err}")
    sys.exit(1)
PYEOF
echo ""

# Check for dependency conflicts
echo "7. Checking for remaining conflicts..."
pipdeptree --warn=fail > /tmp/pipdeptree_output.txt 2>&1 || {
    echo "   ⚠ Some conflicts remain (see /tmp/pipdeptree_output.txt)"
    grep "Warning!!!" /tmp/pipdeptree_output.txt | head -20
}
echo ""

# Run basic tests if available
echo "8. Running basic import tests..."
python3 << 'PYEOF'
try:
    from shared.llm_providers import get_provider
    from shared.config import Config
    from shared.utils.async_adapter import async_to_sync
    print("   ✓ Core imports successful")
except Exception as e:
    print(f"   ⚠ Import error: {e}")
PYEOF
echo ""

echo "=========================================="
echo "Quick fixes complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review full audit report: DEPENDENCY_AUDIT_REPORT.md"
echo "2. Run test suite: pytest tests/"
echo "3. Update requirements.txt with pinned versions"
echo "4. Test dependent projects (beltalowda, swarm, etc.)"
echo ""
echo "Backup location: requirements.txt.backup-*"
echo ""
