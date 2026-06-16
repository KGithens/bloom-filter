"""Benchmark Bloom filter add and lookup throughput.

Uses stdlib ``timeit`` for throughput (ops/s) and optional ``cProfile`` to see
where time is spent (expect ``sha256`` to dominate).

Run:
    python3 profile_bloom_filter.py              # throughput benchmarks
    python3 profile_bloom_filter.py --profile    # add cProfile breakdown
    python3 profile_bloom_filter.py --quick      # fast run (used by tests)

Benchmarks are for local investigation only — not run in CI (timings vary by machine).
"""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import timeit
from statistics import median

from bloom_filter import BloomFilter

# Defaults mirror demo.py sizing: m ≈ 10 bits per expected item, k ≈ 7.
DEFAULT_SIZE = 20_000
DEFAULT_HASHES = 7
DEFAULT_ITEMS = 5_000
DEFAULT_REPEAT = 5
DEFAULT_NUMBER = 50


def _ops_per_second(ops: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return ops / elapsed_seconds


def _summarize_timings(label: str, samples: list[float], ops_per_sample: int) -> None:
    """Print median and best of several timeit samples.

    ``timeit.repeat`` returns one elapsed time per repeat (each repeat runs
    ``number`` loops of the statement). ``ops_per_sample`` is the total Bloom
    operations timed in one sample (keys × loops).
    """
    med_elapsed = median(samples)
    best_elapsed = min(samples)
    print(f"{label}")
    print(
        f"  median: {med_elapsed / ops_per_sample * 1e6:.1f} µs/op"
        f"  ({_ops_per_second(ops_per_sample, med_elapsed):,.0f} ops/s)"
    )
    print(
        f"  best:   {best_elapsed / ops_per_sample * 1e6:.1f} µs/op"
        f"  ({_ops_per_second(ops_per_sample, best_elapsed):,.0f} ops/s)"
    )


def benchmark_add(size: int, num_hashes: int, item_count: int, repeat: int, number: int) -> None:
    """Time many ``add`` calls on a fresh filter each repeat."""
    # setup/stmt are Python source strings that timeit exec's — keep lines flush-left
    # (indent here becomes part of the string). {size} etc. are filled in by the f-string.
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
keys = ["add-" + str(i) for i in range({item_count})]
"""
    stmt = """
for key in keys:
    bloom.add(key)
"""
    samples = timeit.repeat(stmt, setup=setup, repeat=repeat, number=number)
    _summarize_timings("add", samples, item_count * number)


def benchmark_might_contain_hits(
    size: int, num_hashes: int, item_count: int, repeat: int, number: int
) -> None:
    """Time lookups for keys already inserted (all k bits should be set)."""
    # setup/stmt: flush-left strings executed by timeit (see benchmark_add).
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
keys = ["hit-" + str(i) for i in range({item_count})]
for key in keys:
    bloom.add(key)
"""
    stmt = """
for key in keys:
    bloom.might_contain(key)
"""
    samples = timeit.repeat(stmt, setup=setup, repeat=repeat, number=number)
    _summarize_timings("might_contain (hits)", samples, item_count * number)


def benchmark_might_contain_misses(
    size: int, num_hashes: int, item_count: int, repeat: int, number: int
) -> None:
    """Time lookups for keys never inserted (often exits early on first unset bit)."""
    # setup/stmt: flush-left strings executed by timeit (see benchmark_add).
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
for i in range({item_count}):
    bloom.add("present-" + str(i))
keys = ["miss-" + str(i) for i in range({item_count})]
"""
    stmt = """
for key in keys:
    bloom.might_contain(key)
"""
    samples = timeit.repeat(stmt, setup=setup, repeat=repeat, number=number)
    _summarize_timings("might_contain (misses)", samples, item_count * number)


def run_cprofile(size: int, num_hashes: int, item_count: int) -> None:
    """Show which functions dominate wall time (complements timeit throughput).

    timeit answers "how fast?"; cProfile answers "where?". Useful to confirm
    hashing — not bit operations — is the bottleneck before swapping hash algorithms.
    """
    bloom = BloomFilter(size=size, num_hashes=num_hashes)
    keys = [f"profile-{i}" for i in range(item_count)]

    def workload() -> None:
        for key in keys:
            bloom.add(key)
        for key in keys:
            bloom.might_contain(key)

    profiler = cProfile.Profile()
    profiler.enable()
    workload()
    profiler.disable()

    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream).sort_stats("cumulative")
    stats.print_stats(15)
    print("cProfile (top 15 by cumulative time)")
    print(stream.getvalue())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=DEFAULT_SIZE, help="Bloom filter m (bits)")
    parser.add_argument("--hashes", type=int, default=DEFAULT_HASHES, help="Bloom filter k")
    parser.add_argument("--items", type=int, default=DEFAULT_ITEMS, help="Keys per benchmark batch")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="timeit repeat count")
    parser.add_argument("--number", type=int, default=DEFAULT_NUMBER, help="timeit loops per repeat")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Small repeat/number for smoke tests",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Print cProfile output for a mixed add + lookup workload",
    )
    args = parser.parse_args()

    repeat = 2 if args.quick else args.repeat
    number = 5 if args.quick else args.number

    print("Bloom filter benchmarks")
    print("=" * 40)
    print(f"m={args.size:,}  k={args.hashes}  batch={args.items:,}  repeat={repeat}  number={number}")
    print()

    # Three workloads: insert, positive lookup, negative lookup.
    benchmark_add(args.size, args.hashes, args.items, repeat, number)
    print()
    benchmark_might_contain_hits(args.size, args.hashes, args.items, repeat, number)
    print()
    benchmark_might_contain_misses(args.size, args.hashes, args.items, repeat, number)

    if args.profile:
        print()
        run_cprofile(args.size, args.hashes, min(args.items, 2_000))


if __name__ == "__main__":
    main()
