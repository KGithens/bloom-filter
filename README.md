# Bloom Filter Demo

A Bloom filter implementation in Python with deduplication, sharded-cache, and profiling demos.

## What is a Bloom Filter?

A Bloom filter is a space-efficient probabilistic data structure for set membership. It uses:

- A fixed-size **bit array** of length `m`
- **`k` hash functions** that map each item to `k` bit positions

To **add** an item, set all `k` bits to 1. To **check membership**, verify all `k` bits are 1.

## False Positives and False Negatives

- **No false negatives**: if an item was added, `might_contain` always returns `True`.
- **Possible false positives**: an item that was never added may still appear present because other items happened to set the same bits.

There is no way to remove items without risking false negatives (unless you use a counting or deletion-capable variant).

## Tradeoffs

| Choice | Effect |
|--------|--------|
| Larger `m` | Lower false-positive rate, more memory |
| Larger `k` | Fewer false positives up to a point, then more collisions |
| Smaller `m` or `k` | Less memory, higher false-positive rate |

For `n` items, a common rule of thumb is `m ≈ 10n` bits and `k ≈ 7` hash functions for ~1% false-positive rate.

## How This Implementation Works

1. **`BloomFilter(size, num_hashes)`** — creates a bit array of `size` bits and uses `num_hashes` hash functions.
2. **Hashing** — one SHA-256 digest yields two base hashes (`h1`, `h2` from the first 16 bytes). All `k` indices use double hashing: `h_i = (h1 + i × h2) mod m`, so hash work is O(1) per item instead of O(k).
3. **`add(item)`** — sets the `k` bit positions for the item.
4. **`might_contain(item)`** — returns `True` only if all `k` bits are set.

## Deduplication demo

```bash
git clone https://github.com/KGithens/bloom-filter.git
cd bloom-filter
python3 demo.py
```

Generates ~10,000 random strings (sampled from ~2,000 unique values), deduplicates with the Bloom filter, and compares against a Python `set` to report totals, unique counts, and false positives. The auxiliary `seen` set in `demo.py` is only for measuring false positives during the walkthrough.

## Sharded cache demo

```bash
python3 redis_bloom_demo.py
```

Simulates a distributed image cache split across Redis shards, with one Bloom filter per shard. On a cache miss, the Bloom filter short-circuits the lookup and skips the shard entirely; on a possible hit, the demo falls through to the simulated Redis `GET`. Reports how many round-trips were avoided and illustrates stale positives after a Redis-only eviction (standard Bloom filters cannot delete).

## Run Tests

```bash
python3 -m unittest test_bloom_filter.py -v
```

## CI

Pull requests and pushes to `main` run the same test suite in GitHub Actions (Python 3.11–3.13).

## Profiling

```bash
python3 profile_bloom_filter.py
python3 profile_bloom_filter.py --profile   # cProfile: where time goes (expect sha256 at the top)
```

Benchmarks `add`, `might_contain` on hits, and `might_contain` on misses with stdlib `timeit` (median and best µs/op and ops/s). Use `--profile` to confirm hashing — not bit operations — dominates before swapping hash algorithms. Timings vary by machine, so benchmarks are local only; CI smoke-tests the script with `--quick` but does not assert performance numbers.

## Future work

- Derive `m` and `k` from expected item count and target false-positive rate
- Add union/serialization or a counting variant for deletion
- Swap SHA-256 for a faster non-cryptographic hash in production
- Statistical false-positive rate checks in tests
