"""Demonstrate Bloom filter deduplication on a dataset with duplicates."""

from __future__ import annotations

import random
import string

from bloom_filter import BloomFilter

DATASET_SIZE = 10_000
UNIQUE_POOL_SIZE = 2_000
# m ≈ 10 bits per expected unique item; k ≈ 7 is a common choice for low FP rate.
FILTER_SIZE = UNIQUE_POOL_SIZE * 10
NUM_HASHES = 7


def random_string(length: int = 12) -> str:
    """Generate a random alphanumeric string."""
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choices(alphabet, k=length))


def generate_dataset(size: int, unique_pool_size: int) -> list[str]:
    """Build a dataset by sampling from a smaller pool to create duplicates."""
    pool = [random_string() for _ in range(unique_pool_size)]
    return [random.choice(pool) for _ in range(size)]


def deduplicate_with_bloom(items: list[str], bloom: BloomFilter) -> tuple[list[str], int]:
    """Keep first occurrence of each item; count false positives along the way."""
    unique_items: list[str] = []
    seen: set[str] = set()
    false_positives = 0

    for item in items:
        if bloom.might_contain(item):
            if item not in seen:
                false_positives += 1
            continue
        bloom.add(item)
        unique_items.append(item)
        seen.add(item)

    return unique_items, false_positives


def main() -> None:
    random.seed(42)
    dataset = generate_dataset(DATASET_SIZE, UNIQUE_POOL_SIZE)

    bloom = BloomFilter(size=FILTER_SIZE, num_hashes=NUM_HASHES)
    bloom_unique, false_positives = deduplicate_with_bloom(dataset, bloom)

    actual_unique = list(dict.fromkeys(dataset))  # preserves order
    actual_unique_set = set(actual_unique)

    print("Bloom Filter Deduplication Demo")
    print("=" * 40)
    print(f"Total items:              {len(dataset):,}")
    print(f"Actual unique items:      {len(actual_unique):,}")
    print(f"Bloom filter unique count:{len(bloom_unique):,}")
    print(f"False positives:          {false_positives:,}")
    print()
    print(f"Filter size (m):          {bloom.size:,} bits")
    print(f"Hash functions (k):       {bloom.num_hashes}")
    print(f"Memory (approx):          {bloom.memory_bytes:,} bytes")

    # Sanity check: every bloom-accepted item should be in the actual unique set.
    extras = [item for item in bloom_unique if item not in actual_unique_set]
    if extras:
        print(f"\nUnexpected items not in actual set: {len(extras)}")
    else:
        print("\nAll bloom-filter results are subset of actual unique items (no false negatives).")


if __name__ == "__main__":
    main()
