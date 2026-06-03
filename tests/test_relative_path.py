"""Test script to verify relative path conversion."""
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import BASE_DIR

# Copy the helper function for testing
def _get_relative_path(absolute_path: Path, base_dir: Path) -> str:
    """Convert absolute path to relative path from base directory."""
    try:
        # Convert to relative path and use forward slashes for consistency
        rel_path = absolute_path.relative_to(base_dir)
        return str(rel_path).replace('\\', '/')
    except ValueError:
        # If path is not relative to base_dir, return as-is
        return str(absolute_path)

# Test 1: Basic conversion
test_path = Path(r"D:\AI-PROJECT\RAG\SpecRag\data\extracted_images\A2DP_v1.4-1.pdf_p17.png")
relative = _get_relative_path(test_path, BASE_DIR)

print("=" * 60)
print("Test 1: Basic Path Conversion")
print("=" * 60)
print(f"BASE_DIR:        {BASE_DIR}")
print(f"Absolute path:   {test_path}")
print(f"Relative path:   {relative}")
print()

# Test 2: Verify format
expected = "data/extracted_images/A2DP_v1.4-1.pdf_p17.png"
if relative == expected:
    print("[OK] Test PASSED: Path format is correct!")
    print(f"  Expected: {expected}")
    print(f"  Got:      {relative}")
else:
    print("[ERROR] Test FAILED: Path format is incorrect!")
    print(f"  Expected: {expected}")
    print(f"  Got:      {relative}")

print()
print("=" * 60)
