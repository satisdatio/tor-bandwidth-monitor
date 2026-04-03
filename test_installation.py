#!/usr/bin/env python3
"""
Simple test script to verify Tor Monitor Pro installation.
Run with: python test_installation.py
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from tor_monitor_pro.config import Config
        print("✅ Config import successful")
    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False

    try:
        from tor_monitor_pro.database import Database
        print("✅ Database import successful")
    except ImportError as e:
        print(f"❌ Database import failed: {e}")
        return False

    try:
        from tor_monitor_pro.controller import MultiRelayController
        print("✅ Controller import successful")
    except ImportError as e:
        print(f"❌ Controller import failed: {e}")
        return False

    try:
        from tor_monitor_pro.metrics import MetricsCollector
        print("✅ Metrics import successful")
    except ImportError as e:
        print(f"❌ Metrics import failed: {e}")
        return False

    try:
        from tor_monitor_pro.alerts import AlertManager
        print("✅ Alerts import successful")
    except ImportError as e:
        print(f"❌ Alerts import failed: {e}")
        return False

    try:
        from tor_monitor_pro.anomaly import AnomalyDetector
        print("✅ Anomaly import successful")
    except ImportError as e:
        print(f"❌ Anomaly import failed: {e}")
        return False

    try:
        from tor_monitor_pro.audit import AuditLogger
        print("✅ Audit import successful")
    except ImportError as e:
        print(f"❌ Audit import failed: {e}")
        return False

    try:
        from tor_monitor_pro.plugins import PluginManager
        print("✅ Plugins import successful")
    except ImportError as e:
        print(f"❌ Plugins import failed: {e}")
        return False

    try:
        from tor_monitor_pro.api.server import create_api_server
        print("✅ API import successful")
    except ImportError as e:
        print(f"❌ API import failed: {e}")
        return False

    try:
        from tor_monitor_pro.ui.tui import TorMonitorTUI
        print("✅ TUI import successful")
    except ImportError as e:
        print(f"❌ TUI import failed: {e}")
        return False

    return True

def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")

    try:
        from tor_monitor_pro.config import Config
        config = Config()
        print("✅ Configuration loaded successfully")
        print(f"   App name: {config.app_name}")
        print(f"   Version: {config.version}")
        print(f"   Debug: {config.debug}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_database():
    """Test database initialization."""
    print("\nTesting database...")

    try:
        from tor_monitor_pro.database import Database
        # Use in-memory SQLite for testing
        db = Database("sqlite:///:memory:")
        db.init_db()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Tor Monitor Pro Installation Test")
    print("=" * 40)

    tests = [
        ("Import Tests", test_imports),
        ("Configuration Test", test_config),
        ("Database Test", test_database),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n{name}")
        print("-" * len(name))
        if test_func():
            passed += 1

    print("\n" + "=" * 40)
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed! Tor Monitor Pro is ready to use.")
        print("\nNext steps:")
        print("1. Configure your .env file (see .env.example)")
        print("2. Run pre-flight checks: tor-monitor-pro-check")
        print("3. Start the application: tor-monitor-pro")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("1. Install dependencies: pip install -e .")
        print("2. Check Python version (3.9+ required)")
        print("3. Verify all files are present")
        return 1

if __name__ == "__main__":
    sys.exit(main())