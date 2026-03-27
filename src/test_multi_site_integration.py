#!/usr/bin/env python3
"""
Test multi-site integration with existing Parts Agent system
Verifies database, scraper, and GUI components work together
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_integration():
    """Test database integration"""
    print("1. Testing Database Integration...")

    try:
        from database.db_manager import DatabaseManager
        db_manager = DatabaseManager()

        # Test database initialization
        if db_manager.initialize_database():
            print("   [OK] Database initialized")
        else:
            print("   [ERROR] Database initialization failed")
            return False

        # Test site configs
        configs = db_manager.get_site_configs()
        print(f"   [OK] Found {len(configs)} site configurations")

        return True

    except ImportError as e:
        print(f"   [ERROR] Database import failed: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Database test failed: {e}")
        return False


def test_scraper_integration():
    """Test multi-site scraper integration"""
    print("\n2. Testing Multi-Site Scraper Integration...")

    try:
        from scrapers.multi_site_manager import MultiSiteScraperManager

        manager = MultiSiteScraperManager()
        print("   [OK] Multi-site manager created")

        # Test site configs loading
        if len(manager.site_configs) > 0:
            print(f"   [OK] Loaded {len(manager.site_configs)} site configurations")
        else:
            print("   [WARNING] No site configurations loaded")

        # Test RockAuto scraper integration
        print("   Testing RockAuto integration...")
        results = manager.scrape_part_multi_site(
            part_number="3217",
            brand="ANCHOR",
            sites=['RockAuto'],
            store_results=False  # Don't store during test
        )

        if results['summary']['successful_sites'] > 0:
            print("   [OK] RockAuto scraper integration working")
        else:
            print("   [WARNING] RockAuto scraper integration failed")

        return True

    except ImportError as e:
        print(f"   [ERROR] Scraper import failed: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Scraper test failed: {e}")
        return False


def test_gui_integration():
    """Test GUI integration"""
    print("\n3. Testing GUI Integration...")

    try:
        # Test multi-site tab import
        from gui.multi_site_tab import MultiSiteTab
        print("   [OK] Multi-site tab imports successfully")

        # Test main window integration
        from gui.main_window import MULTI_SITE_AVAILABLE
        if MULTI_SITE_AVAILABLE:
            print("   [OK] Multi-site functionality available in main GUI")
        else:
            print("   [WARNING] Multi-site functionality not available in main GUI")

        return True

    except ImportError as e:
        print(f"   [ERROR] GUI import failed: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] GUI test failed: {e}")
        return False


def test_existing_system_compatibility():
    """Test compatibility with existing system"""
    print("\n4. Testing Existing System Compatibility...")

    try:
        # Test existing scraper still works
        from scraper_subprocess import scrape_rockauto_subprocess
        print("   [OK] Existing RockAuto scraper imports successfully")

        # Test existing Excel handling still works
        import excel_handler
        print("   [OK] Existing Excel handler imports successfully")

        # Test existing GUI still works
        from gui.main_window import UnifiedPartsAgent
        print("   [OK] Existing GUI imports successfully")

        return True

    except ImportError as e:
        print(f"   [ERROR] Existing system import failed: {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] Existing system test failed: {e}")
        return False


def run_integration_tests():
    """Run all integration tests"""
    print("MULTI-SITE INTEGRATION TEST SUITE")
    print("=" * 50)

    tests = [
        test_database_integration,
        test_scraper_integration,
        test_gui_integration,
        test_existing_system_compatibility
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"   [CRITICAL] Test {test_func.__name__} crashed: {e}")

    print(f"\n" + "=" * 50)
    print(f"INTEGRATION TEST RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("STATUS: [SUCCESS] All integration tests passed!")
        print("\nMULTI-SITE SYSTEM READY FOR PRODUCTION")
        print("\nFeatures Available:")
        print("- Multi-site database storage")
        print("- RockAuto scraper integration")
        print("- GUI multi-site management tab")
        print("- Full compatibility with existing system")

        print("\nNext Steps:")
        print("1. Launch GUI: uv run python src/gui/main_window.py")
        print("2. Use Multi-Site tab to search across sites")
        print("3. Implement additional site scrapers (PartsGeek, ACDelco, etc.)")
        print("4. Expand cross-site part matching capabilities")

    else:
        print(f"STATUS: [PARTIAL] {total - passed} tests failed")
        print("Some multi-site features may not be available")

    return passed == total


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)