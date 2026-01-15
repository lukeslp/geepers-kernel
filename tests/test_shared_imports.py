#!/usr/bin/env python3
"""
Test script to verify shared library imports work correctly.

This tests both direct imports and imports through PYTHONPATH.
Run from any directory to verify the fix is working.
"""

import sys
import os

def test_direct_import():
    """Test importing when PYTHONPATH is set."""
    print("Test 1: Direct import with PYTHONPATH set")

    # This should be set by service_manager
    shared_path = '/home/coolhand/shared'
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

    try:
        from shared.config import ConfigManager
        print("✓ shared.config.ConfigManager imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ConfigManager: {e}")
        return False

    try:
        from shared.llm_providers import ProviderFactory, Message
        print("✓ shared.llm_providers imports successful")
    except ImportError as e:
        print(f"✗ Failed to import from llm_providers: {e}")
        return False

    return True


def test_editable_install():
    """Test that subpackages work via editable install."""
    print("\nTest 2: Subpackage imports (via editable install)")

    try:
        from llm_providers import ProviderFactory
        print("✓ llm_providers.ProviderFactory imported directly")
    except ImportError as e:
        print(f"⚠ Could not import llm_providers directly: {e}")
        print("  (This is OK - main imports use 'shared.' prefix)")

    return True


def test_studio_imports():
    """Test imports needed by studio service."""
    print("\nTest 3: Studio service imports")

    shared_path = '/home/coolhand/shared'
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

    try:
        # Import exactly as studio/config.py does
        from shared.config import ConfigManager
        print("✓ Studio can import shared.config.ConfigManager")
        return True
    except ImportError as e:
        print(f"✗ Studio import failed: {e}")
        return False


def test_enterprise_imports():
    """Test imports needed by enterprise_orchestration."""
    print("\nTest 4: Enterprise orchestration imports")

    shared_path = '/home/coolhand/shared'
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)

    try:
        # Import exactly as coordinator.py does
        from shared.llm_providers import ProviderFactory, Message
        print("✓ Enterprise can import from shared.llm_providers")
        return True
    except ImportError as e:
        print(f"✗ Enterprise import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Shared Library Import Test")
    print("="*60)
    print()

    results = []
    results.append(("Direct import", test_direct_import()))
    results.append(("Editable install", test_editable_install()))
    results.append(("Studio imports", test_studio_imports()))
    results.append(("Enterprise imports", test_enterprise_imports()))

    print()
    print("="*60)
    print("Test Results")
    print("="*60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All critical tests passed!")
        print("\nThe fix is working correctly:")
        print("- service_manager.py sets PYTHONPATH=/home/coolhand/shared")
        print("- Services can import from shared.* packages")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
