"""Bloom filters in front of a sharded image cache (simulated Redis).

Each shard has its own in-memory "Redis" dict and its own Bloom filter.
On GET: check the shard's Bloom filter first; skip the shard lookup if absent.
On SET: write to Redis and add the key to that shard's filter.

This demo uses dicts instead of real Redis so it runs with stdlib only.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from bloom_filter import BloomFilter

# --- Simulated infrastructure -------------------------------------------------

NUM_SHARDS = 4
# Bits per shard; size for ~1k keys/shard at low FP rate (rule of thumb ~10 bits/key).
BLOOM_BITS_PER_SHARD = 10_000
BLOOM_NUM_HASHES = 7


def shard_for_key(key: str, num_shards: int) -> int:
    """Route a cache key to a shard (stable hash, same idea as Redis cluster)."""
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:8], "big") % num_shards


class RedisShard:
    """One shard of the distributed cache."""

    def __init__(self, shard_id: int) -> None:
        self.shard_id = shard_id
        self._store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self._store.get(key)

    def set(self, key: str, value: bytes) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def __len__(self) -> int:
        return len(self._store)


@dataclass
class CacheStats:
    bloom_short_circuits: int = 0  # definite miss: skipped Redis
    redis_lookups: int = 0
    redis_hits: int = 0
    bloom_false_positives: int = 0  # Bloom said maybe, Redis said no


@dataclass
class ShardedImageCache:
    """Image cache with one Bloom filter per Redis shard."""

    num_shards: int = NUM_SHARDS
    bloom_bits: int = BLOOM_BITS_PER_SHARD
    bloom_hashes: int = BLOOM_NUM_HASHES
    shards: list[RedisShard] = field(init=False)
    filters: list[BloomFilter] = field(init=False)
    stats: CacheStats = field(default_factory=CacheStats)

    def __post_init__(self) -> None:
        self.shards = [RedisShard(i) for i in range(self.num_shards)]
        self.filters = [
            BloomFilter(size=self.bloom_bits, num_hashes=self.bloom_hashes)
            for _ in range(self.num_shards)
        ]

    def _shard_index(self, key: str) -> int:
        return shard_for_key(key, self.num_shards)

    def put_image(self, image_id: str, data: bytes) -> None:
        """Cache an image: Redis SET + Bloom add on the owning shard."""
        shard_idx = self._shard_index(image_id)
        self.shards[shard_idx].set(image_id, data)
        self.filters[shard_idx].add(image_id)

    def get_image(self, image_id: str) -> bytes | None:
        """Cache GET with Bloom guard: skip Redis when filter says absent."""
        shard_idx = self._shard_index(image_id)
        bloom = self.filters[shard_idx]
        redis = self.shards[shard_idx]

        if not bloom.might_contain(image_id):
            self.stats.bloom_short_circuits += 1
            return None

        self.stats.redis_lookups += 1
        value = redis.get(image_id)
        if value is not None:
            self.stats.redis_hits += 1
        else:
            self.stats.bloom_false_positives += 1
        return value

    def evict_from_redis_only(self, image_id: str) -> None:
        """Evict from Redis without updating Bloom — shows stale-positive risk."""
        shard_idx = self._shard_index(image_id)
        self.shards[shard_idx].delete(image_id)


# --- Demo ---------------------------------------------------------------------


def main() -> None:
    random.seed(42)
    cache = ShardedImageCache()

    # Warm cache: 500 images across shards.
    cached_ids = [f"img-{i:05d}" for i in range(500)]
    for image_id in cached_ids:
        cache.put_image(image_id, b"fake-image-bytes")

    # Lookup mix: 500 cached, 2000 uncached (never in Redis).
    lookup_ids = cached_ids + [f"img-miss-{i:05d}" for i in range(2_000)]
    random.shuffle(lookup_ids)

    for image_id in lookup_ids:
        cache.get_image(image_id)

    print("Sharded image cache + Bloom filter demo")
    print("=" * 44)
    print(f"Shards:                      {cache.num_shards}")
    print(f"Images in Redis:             {sum(len(s) for s in cache.shards)}")
    print(f"Total lookups:               {len(lookup_ids):,}")
    print()
    print(f"Bloom short-circuits (skip Redis): {cache.stats.bloom_short_circuits:,}")
    print(f"Redis lookups:                     {cache.stats.redis_lookups:,}")
    print(f"Redis hits:                        {cache.stats.redis_hits:,}")
    print(f"Bloom false positives:             {cache.stats.bloom_false_positives:,}")
    print()
    saved_pct = 100 * cache.stats.bloom_short_circuits / len(lookup_ids)
    print(f"Redis round-trips avoided:         {saved_pct:.1f}%")

    # Eviction without Bloom update: filter still says "maybe".
    victim = cached_ids[0]
    cache.evict_from_redis_only(victim)
    print()
    print(f"After Redis-only evict of {victim}:")
    print(f"  Bloom might_contain: {cache.filters[cache._shard_index(victim)].might_contain(victim)}")
    print(f"  Redis get:           {cache.get_image(victim) is None}")
    print("  (Bloom still positive → extra Redis GET; can't delete from standard Bloom.)")


if __name__ == "__main__":
    main()
