# Bloom Filter Demo

A small, interview-friendly Bloom filter implementation in Python with a deduplication demo.

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
2. **Hashing** — each hash function salts the input with an index (`"0:item"`, `"1:item"`, …) and runs SHA-256; the first 8 bytes map to a bit index via modulo.
3. **`add(item)`** — sets the `k` bit positions for the item.
4. **`might_contain(item)`** — returns `True` only if all `k` bits are set.

## Run the Demo

```bash
git clone https://github.com/KGithens/bloom-filter.git
cd bloom-filter
python3 demo.py
```

The demo generates ~10,000 random strings (sampled from ~2,000 unique values), deduplicates with the Bloom filter, and compares against a Python `set` to report totals, unique counts, and false positives.

## Possible Improvements

With more time, you could:

- Compute optimal `m` and `k` from expected item count and target false-positive rate
- Add a `union` operation or serialization (save/load bit array)
- Swap SHA-256 for faster non-cryptographic hashes (e.g. MurmurHash) in production
- Track and report estimated false-positive probability
- Support deletion with a counting Bloom filter
- Add unit tests for edge cases and false-positive behavior
