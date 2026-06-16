"""Benchmark Bloom filter add and lookup throughput (stdlib timeit + optional cProfile)."""

from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import timeit
from statistics import median

from bloom_filter import BloomFilter

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
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
keys = [f"add-{{i}}" for i in range({item_count})]
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
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
keys = [f"hit-{{i}}" for i in range({item_count})]
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
    setup = f"""
from bloom_filter import BloomFilter
bloom = BloomFilter(size={size}, num_hashes={num_hashes})
for i in range({item_count}):
    bloom.add(f"present-{{i}}")
keys = [f"miss-{{i}}" for i in range({item_count})]
"""
    stmt = """
for key in keys:
    bloom.might_contain(key)
"""
    samples = timeit.repeat(stmt, setup=setup, repeat=repeat, number=number)
    _summarize_timings("might_contain (misses)", samples, item_count * number)


def run_cprofile(size: int, num_hashes: int, item_count: int) -> None:
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
