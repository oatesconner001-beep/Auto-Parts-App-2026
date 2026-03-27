"""
Test script for enhanced image comparison - verify CLIP fix and performance
"""

import time
from image_compare_enhanced import compare_part_images_enhanced, _load_clip_model

def test_clip_model():
    """Test CLIP model loading and basic functionality"""
    print("Testing CLIP model...")

    try:
        model, preprocess = _load_clip_model()
        if model is not None:
            print("[OK] CLIP model loaded successfully")
            # Test device availability
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"[OK] Using device: {device}")
            return True
        else:
            print("[ERROR] CLIP model failed to load")
            return False
    except Exception as e:
        print(f"[ERROR] CLIP test failed: {e}")
        return False

def test_enhanced_comparison():
    """Test enhanced comparison with known working images"""
    print("\nTesting enhanced comparison...")

    # Test data with known auto part images
    anchor_data = {
        "image_url": "https://www.rockauto.com/info/28/3217-000__ra_m.jpg",
        "brand": "ANCHOR",
        "part_number": "3217"
    }

    skp_data = {
        "image_url": "https://www.rockauto.com/info/983/SKM3217_1___ra_m.jpg",
        "brand": "SKP",
        "part_number": "SKM3217"
    }

    try:
        start_time = time.time()
        result = compare_part_images_enhanced(anchor_data, skp_data)
        elapsed = time.time() - start_time

        print(f"[OK] Comparison completed in {elapsed:.1f}s")
        print(f"  Verdict: {result['verdict']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Score: {result['similarity_score']:.2f}")
        print(f"  Method scores: {result['method_scores']}")
        print(f"  Reasoning: {result['reasoning']}")

        if result['error']:
            print(f"[WARNING] Error during comparison: {result['error']}")
            return False

        # Check if CLIP worked
        if 'clip_semantic' in result['method_scores']:
            clip_score = result['method_scores']['clip_semantic']
            if clip_score > 0:
                print(f"[OK] CLIP working - semantic score: {clip_score:.2f}")
            else:
                print(f"[WARNING] CLIP returned 0 score")
        else:
            print(f"[ERROR] CLIP not in results")
            return False

        return True

    except Exception as e:
        print(f"[ERROR] Enhanced comparison failed: {e}")
        return False

if __name__ == "__main__":
    print(">> Enhanced Image Comparison Test")
    print("=" * 50)

    clip_ok = test_clip_model()
    comparison_ok = test_enhanced_comparison()

    print("\n" + "=" * 50)
    if clip_ok and comparison_ok:
        print("[SUCCESS] All tests passed - enhanced system ready!")
    else:
        print("[FAILURE] Some tests failed - needs debugging")
        if not clip_ok:
            print("  - CLIP model issues")
        if not comparison_ok:
            print("  - Enhanced comparison issues")