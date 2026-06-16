"""Tests for BloomFilter correctness properties."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from bloom_filter import BloomFilter


class BloomFilterTests(unittest.TestCase):
    def test_rejects_non_positive_size(self) -> None:
        with self.assertRaises(ValueError):
            BloomFilter(size=0, num_hashes=3)
        with self.assertRaises(ValueError):
            BloomFilter(size=-1, num_hashes=3)

    def test_rejects_non_positive_num_hashes(self) -> None:
        with self.assertRaises(ValueError):
            BloomFilter(size=100, num_hashes=0)
        with self.assertRaises(ValueError):
            BloomFilter(size=100, num_hashes=-1)

    def test_unknown_not_in_empty_filter(self) -> None:
        bloom = BloomFilter(size=1_000, num_hashes=5)
        self.assertFalse(bloom.might_contain("never-added"))

    def test_added_items_always_found(self) -> None:
        bloom = BloomFilter(size=2_000, num_hashes=7)
        items = ["alpha", "bravo", "charlie", "delta", "echo"]

        for item in items:
            bloom.add(item)

        for item in items:
            self.assertTrue(bloom.might_contain(item))

    def test_count_tracks_add_operations(self) -> None:
        bloom = BloomFilter(size=500, num_hashes=3)
        bloom.add("one")
        bloom.add("two")
        bloom.add("one")
        self.assertEqual(bloom.count, 3)

    def test_config_properties(self) -> None:
        bloom = BloomFilter(size=2_048, num_hashes=7)
        self.assertEqual(bloom.size, 2_048)
        self.assertEqual(bloom.num_hashes, 7)
        self.assertEqual(bloom.memory_bytes, 256)

    def test_indices_in_range(self) -> None:
        bloom = BloomFilter(size=500, num_hashes=5)
        for index in bloom._hash_indices("bounds-check"):
            self.assertGreaterEqual(index, 0)
            self.assertLess(index, bloom.size)


class DoubleHashingTests(unittest.TestCase):
    def test_indices_are_distinct(self) -> None:
        bloom = BloomFilter(size=10_000, num_hashes=7)
        indices = bloom._hash_indices("distinct-check")
        self.assertEqual(len(indices), len(set(indices)))

    def test_h2_zero_uses_nonzero_step(self) -> None:
        bloom = BloomFilter(size=1_000, num_hashes=5)
        digest = b"\x01" * 8 + b"\x00" * 8 + b"\x00" * 16
        mock_hash = MagicMock()
        mock_hash.digest.return_value = digest

        with patch.object(hashlib, "sha256", return_value=mock_hash):
            indices = bloom._hash_indices("h2-zero")

        self.assertEqual(len(indices), len(set(indices)))

    def test_single_digest_per_lookup(self) -> None:
        bloom = BloomFilter(size=1_000, num_hashes=7)
        with patch.object(hashlib, "sha256", wraps=hashlib.sha256) as sha256_mock:
            bloom._hash_indices("single-digest")
        self.assertEqual(sha256_mock.call_count, 1)


class ProfileBenchmarkTests(unittest.TestCase):
    def test_profile_script_exits_zero_in_quick_mode(self) -> None:
        result = subprocess.run(
            [sys.executable, "profile_bloom_filter.py", "--quick"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
