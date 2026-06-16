"""A Bloom filter implementation using SHA-256 and double hashing."""

from __future__ import annotations

import hashlib


class BloomFilter:
    """Probabilistic set membership structure with no false negatives.

    A Bloom filter uses a fixed-size bit array and k independent hash functions.
    Items can be added; membership queries may return false positives but never
    false negatives (if an item was added, might_contain always returns True).

    Args:
        size: Number of bits in the bit array (m).
        num_hashes: Number of hash functions to use (k).
    """

    def __init__(self, size: int, num_hashes: int) -> None:
        if size <= 0:
            raise ValueError("size must be positive")
        if num_hashes <= 0:
            raise ValueError("num_hashes must be positive")

        self._size = size
        self._num_hashes = num_hashes
        self._bits = bytearray((size + 7) // 8)
        self._count = 0

    @property
    def size(self) -> int:
        """Number of bits in the filter."""
        return self._size

    @property
    def num_hashes(self) -> int:
        """Number of hash functions used."""
        return self._num_hashes

    @property
    def count(self) -> int:
        """Number of items added (not necessarily unique)."""
        return self._count

    @property
    def memory_bytes(self) -> int:
        """Approximate memory used by the underlying bit array."""
        return len(self._bits)

    def add(self, item: str) -> None:
        """Insert an item into the filter."""
        for index in self._hash_indices(item):
            self._set_bit(index)
        self._count += 1

    def might_contain(self, item: str) -> bool:
        """Return True if the item might be in the filter (no false negatives)."""
        return all(self._get_bit(index) for index in self._hash_indices(item))

    def _hash_indices(self, item: str) -> list[int]:
        """Compute k bit positions via double hashing: one SHA-256, then h_i = h1 + i*h2."""
        digest = hashlib.sha256(item.encode()).digest()
        h1 = int.from_bytes(digest[:8], byteorder="big")
        h2 = int.from_bytes(digest[8:16], byteorder="big")
        if h2 == 0:
            h2 = 1

        return [(h1 + i * h2) % self._size for i in range(self._num_hashes)]

    def _set_bit(self, index: int) -> None:
        byte_index, bit_offset = divmod(index, 8)
        self._bits[byte_index] |= 1 << bit_offset

    def _get_bit(self, index: int) -> bool:
        byte_index, bit_offset = divmod(index, 8)
        return bool(self._bits[byte_index] & (1 << bit_offset))
