#!/usr/bin/env python3
"""
System test for Dialed components.
Tests database, services, and backend without full integration.
"""

import time
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from backend.database import (
    init_db,
    insert_gaze_log,
    insert_tab_log,
    insert_label,
    get_stats,
    get_gaze_logs,
    get_tab_logs,
    get_labels
)


def test_database():
    """Test database operations."""
    print("=" * 60)
    print("Testing Database Operations")
    print("=" * 60)

    # Initialize
    init_db()
    print("✓ Database initialized")

    # Test gaze log insertion
    ts = time.time()
    insert_gaze_log(
        timestamp=ts,
        eye_off_center=0.3,
        blink=0,
        head_pitch=-5.2,
        head_yaw=2.1,
        head_distance=0.65
    )
    print("✓ Inserted gaze log")

    # Test tab log insertion
    insert_tab_log(
        timestamp=ts + 1,
        domain="github.com",
        title="GitHub Repository",
        idle_state="active",
        keypress_count=42
    )
    print("✓ Inserted tab log")

    # Test label insertion
    insert_label(timestamp=ts + 2, label="focused")
    insert_label(timestamp=ts + 3, label="distracted")
    print("✓ Inserted labels")

    # Test retrieval
    gaze_logs = get_gaze_logs()
    assert len(gaze_logs) >= 1, "No gaze logs found"
    print(f"✓ Retrieved {len(gaze_logs)} gaze log(s)")

    tab_logs = get_tab_logs()
    assert len(tab_logs) >= 1, "No tab logs found"
    print(f"✓ Retrieved {len(tab_logs)} tab log(s)")

    labels = get_labels()
    assert len(labels) >= 2, "Not enough labels found"
    print(f"✓ Retrieved {len(labels)} label(s)")

    # Test stats
    stats = get_stats()
    print(f"\n✓ Stats: {stats['gaze_logs']} gaze, {stats['tab_logs']} tabs, "
          f"{stats['labels']} labels")
    print(f"  Label breakdown: {stats['label_breakdown']}")

    print("\n✅ All database tests passed!\n")
    return True


def test_gaze_service():
    """Test gaze service can be imported and initialized."""
    print("=" * 60)
    print("Testing Gaze Service")
    print("=" * 60)

    try:
        from services.gaze_service import GazeService

        # Test initialization (don't start camera)
        service = GazeService(target_fps=8, enable_preview=False)
        print("✓ GazeService initialized")

        # Test helper methods
        pt1 = (0, 0)
        pt2 = (3, 4)
        dist = service._dist(pt1, pt2)
        assert dist == 5.0, f"Distance calculation wrong: {dist}"
        print("✓ Distance calculation works")

        print("\n✅ Gaze service tests passed!")
        print("   (Skipped camera test - run manually with --preview)")
        print()
        return True

    except Exception as e:
        print(f"❌ Gaze service test failed: {e}")
        return False


def test_label_service():
    """Test label service can be imported."""
    print("=" * 60)
    print("Testing Label Service")
    print("=" * 60)

    try:
        from services.label_service import LabelService

        # Test initialization (don't start listener)
        service = LabelService()
        print("✓ LabelService initialized")

        print("\n✅ Label service tests passed!")
        print("   (Keyboard listener test skipped - run manually)")
        print()
        return True

    except Exception as e:
        print(f"❌ Label service test failed: {e}")
        return False


def test_backend_models():
    """Test FastAPI models can be imported."""
    print("=" * 60)
    print("Testing Backend Models")
    print("=" * 60)

    try:
        from backend.app import TabLog, GazeLog, Label

        # Test TabLog validation
        tab = TabLog(
            timestamp=time.time(),
            domain="example.com",
            title="Example",
            idle_state="active",
            keypress_count=10
        )
        print("✓ TabLog model works")

        # Test GazeLog validation
        gaze = GazeLog(
            timestamp=time.time(),
            eye_off_center=0.5,
            blink=1,
            head_pitch=0.0,
            head_yaw=0.0,
            head_distance=0.7
        )
        print("✓ GazeLog model works")

        # Test Label validation
        label = Label(timestamp=time.time(), label="focused")
        print("✓ Label model works")

        # Test invalid label
        try:
            bad_label = Label(timestamp=time.time(), label="invalid")
            print("❌ Invalid label should have been rejected")
            return False
        except:
            print("✓ Invalid label rejected correctly")

        print("\n✅ Backend model tests passed!\n")
        return True

    except Exception as e:
        print(f"❌ Backend model test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "DIALED SYSTEM TEST" + " " * 25 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # Run tests
    results.append(("Database", test_database()))
    results.append(("Gaze Service", test_gaze_service()))
    results.append(("Label Service", test_label_service()))
    results.append(("Backend Models", test_backend_models()))

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 All tests passed! System is ready.\n")
        print("Next steps:")
        print("  1. Install Chrome extension from chrome-extension/")
        print("  2. Run: python run_all.py")
        print("  3. Start collecting labeled data!\n")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix issues before proceeding.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
