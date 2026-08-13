"""Data-quality checks. Expanded in Phase 2 with duplicate, date-order, and loss-making checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_raw_data_directory_exists():
    assert (REPO_ROOT / "data" / "raw").is_dir()
