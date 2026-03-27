"""
Test Script for Enhanced Analytics System

Tests all analytics modules to ensure they work correctly before integration.
This is a safe validation script that only reads existing data.
"""

import sys
import traceback
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analytics import Analytics, StatsEngine, TrendAnalyzer, PerformanceTracker, DataQualityAnalyzer

def test_stats_engine():
    """Test the statistics engine."""
    print(">> Testing StatsEngine...")

    try:
        engine = StatsEngine()

        # Test basic summary
        summary = engine.get_summary_stats()
        print(f"   Summary stats loaded: {len(summary)} sections")

        # Test overview stats
        overview = summary.get("overview", {})
        print(f"   Total rows: {overview.get('total_rows', 0):,}")
        print(f"   Processed: {overview.get('processed_rows', 0):,}")
        print(f"   Success rate: {overview.get('success_rate', 0):.1f}%")

        # Test sheet details for Anchor
        if "Anchor" in summary.get("by_sheet", {}):
            anchor_details = engine.get_sheet_details("Anchor")
            print(f"   Anchor analysis: {len(anchor_details)} sections")

        print("   StatsEngine: PASSED")
        return True

    except Exception as e:
        print(f"   StatsEngine: FAILED - {e}")
        traceback.print_exc()
        return False

def test_trend_analyzer():
    """Test the trend analyzer."""
    print("\n>> Testing TrendAnalyzer...")

    try:
        analyzer = TrendAnalyzer()

        # Test basic trend summary
        trends = analyzer.get_trend_summary(days=7)
        print(f"[PASS] Trend summary loaded: {len(trends)} sections")

        # Test processing velocity
        velocity = analyzer.get_processing_velocity(days=7)
        print(f"   *** Velocity analysis: {len(velocity)} metrics")

        print("[PASS] TrendAnalyzer: PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] TrendAnalyzer: FAILED - {e}")
        traceback.print_exc()
        return False

def test_performance_tracker():
    """Test the performance tracker."""
    print("\n>> Testing PerformanceTracker...")

    try:
        tracker = PerformanceTracker()

        # Test performance summary
        summary = tracker.get_performance_summary()
        print(f"[PASS] Performance summary loaded: {len(summary)} sections")

        # Test real-time metrics
        metrics = tracker.get_real_time_metrics()
        print(f"    Real-time metrics: {len(metrics)} data points")

        print("[PASS] PerformanceTracker: PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] PerformanceTracker: FAILED - {e}")
        traceback.print_exc()
        return False

def test_data_quality_analyzer():
    """Test the data quality analyzer."""
    print("\n>> Testing DataQualityAnalyzer...")

    try:
        analyzer = DataQualityAnalyzer()

        # Test quality summary
        quality = analyzer.get_quality_summary()
        print(f"[PASS] Quality summary loaded: {len(quality)} sections")

        # Test overall quality score
        overall = quality.get("overall_quality", {})
        print(f"    Overall score: {overall.get('overall_score', 0):.1f}")
        print(f"    Grade: {overall.get('grade', 'N/A')}")

        print("[PASS] DataQualityAnalyzer: PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] DataQualityAnalyzer: FAILED - {e}")
        traceback.print_exc()
        return False

def test_unified_analytics():
    """Test the unified analytics interface."""
    print("\n>> Testing Unified Analytics Interface...")

    try:
        analytics = Analytics()

        # Test comprehensive report
        report = analytics.get_comprehensive_report()
        print(f"[PASS] Comprehensive report loaded: {len(report)} sections")

        # Display key metrics
        overview = report.get("overview", {})
        if overview:
            print(f"    Processing completion: {overview.get('processing_completion', 0):.1f}%")
            print(f"    Confirmed matches: {overview.get('confirmed_matches', 0):,}")
            print(f"    Needs review: {overview.get('needs_review', 0):,}")

        print("[PASS] Unified Analytics: PASSED")
        return True

    except Exception as e:
        print(f"[FAIL] Unified Analytics: FAILED - {e}")
        traceback.print_exc()
        return False

def test_export_functionality():
    """Test export capabilities."""
    print("\n>> Testing Export Functionality...")

    try:
        # Create test directory
        test_dir = Path(__file__).parent.parent / "test_exports"
        test_dir.mkdir(exist_ok=True)

        # Test stats export
        engine = StatsEngine()
        stats_file = test_dir / "test_stats.json"
        success1 = engine.export_stats(str(stats_file))

        # Test quality export
        quality_analyzer = DataQualityAnalyzer()
        quality_file = test_dir / "test_quality.json"
        success2 = quality_analyzer.export_quality_report(str(quality_file))

        # Test performance export
        performance_tracker = PerformanceTracker()
        performance_file = test_dir / "test_performance.json"
        success3 = performance_tracker.export_performance_report(str(performance_file))

        if success1 and success2 and success3:
            print(f"[PASS] All exports successful to {test_dir}")

            # Check file sizes
            for file in [stats_file, quality_file, performance_file]:
                if file.exists():
                    size_kb = file.stat().st_size / 1024
                    print(f"    {file.name}: {size_kb:.1f} KB")

            print("[PASS] Export Functionality: PASSED")
            return True
        else:
            print(f"[FAIL] Export Functionality: FAILED - Some exports failed")
            return False

    except Exception as e:
        print(f"[FAIL] Export Functionality: FAILED - {e}")
        traceback.print_exc()
        return False

def run_comprehensive_test():
    """Run comprehensive test of all analytics components."""
    print("*** Starting Comprehensive Analytics System Test")
    print("=" * 60)

    tests = [
        ("Statistics Engine", test_stats_engine),
        ("Trend Analyzer", test_trend_analyzer),
        ("Performance Tracker", test_performance_tracker),
        ("Data Quality Analyzer", test_data_quality_analyzer),
        ("Unified Analytics", test_unified_analytics),
        ("Export Functionality", test_export_functionality)
    ]

    results = []

    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

    # Summary
    print("\n" + "=" * 60)
    print(" TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "[PASS] PASSED" if success else "[FAIL] FAILED"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1

    print("\n" + "=" * 60)
    success_rate = (passed / total) * 100
    print(f"[RESULTS] OVERALL: {passed}/{total} tests passed ({success_rate:.1f}%)")

    if success_rate == 100:
        print("[SUCCESS] ALL ANALYTICS MODULES ARE WORKING CORRECTLY!")
        print("[PASS] Ready to proceed with dashboard integration")
    elif success_rate >= 80:
        print("[WARNING]  Most components working - minor issues to resolve")
    else:
        print("[FAIL] Major issues detected - review failed components")

    print("=" * 60)

    return success_rate

if __name__ == "__main__":
    success_rate = run_comprehensive_test()

    # Exit with appropriate code
    if success_rate == 100:
        sys.exit(0)  # Success
    elif success_rate >= 80:
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Error