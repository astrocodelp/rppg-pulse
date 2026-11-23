"""Subject-disjoint dev/test split for UBFC-rPPG REALISTIC (42 subjects).

Frozen rule (ubfc_benchmark_plan.md §3):
  1. Collect the actual subject folder IDs (each contains vid.avi + ground_truth.txt).
  2. Sort them lexicographically.
  3. Permute with numpy.random.default_rng(20261204).permutation.
  4. First half -> development, second half -> held-out test.
     (42 subjects -> 21 / 21; for odd n, test gets the extra subject.)

The rule and seed are frozen BEFORE any frame is processed. Run this ONCE
against the real downloaded folders and commit split_manifest.json + its hash.

Usage:
  python3 make_split.py --data-dir /path/to/UBFC-rPPG          # real run
  python3 make_split.py --demo                                # placeholder demo

Environment: Python 3, NumPy (checked with NumPy 2.5.5). Seed 20261204.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SEED = 20261204


def make_split(subject_ids):
    ids = sorted(subject_ids)
    perm = np.random.default_rng(SEED).permutation(len(ids))
    ordered = [ids[i] for i in perm]
    n_dev = len(ids) // 2
    return {
        "seed": SEED,
        "rule": "sorted ids, default_rng(seed).permutation, first half dev, rest test",
        "n_subjects": len(ids),
        "dev": sorted(ordered[:n_dev]),
        "test": sorted(ordered[n_dev:]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", help="UBFC REALISTIC root with subject folders")
    ap.add_argument("--demo", action="store_true",
                    help="placeholder subject1..subject42; NOT the real manifest")
    ap.add_argument("--out", default="split_manifest.json")
    args = ap.parse_args()

    if args.demo:
        ids = [f"subject{i}" for i in range(1, 43)]
        print("DEMO ONLY: placeholder IDs, not the real dataset folders.")
    elif args.data_dir:
        root = Path(args.data_dir)
        ids = [p.name for p in sorted(root.iterdir())
               if p.is_dir() and (p / "vid.avi").exists()]
        if not ids:
            sys.exit(f"No subject folders with vid.avi under {root}")
    else:
        sys.exit("Give --data-dir or --demo")

    manifest = make_split(ids)
    manifest["demo"] = bool(args.demo)
    text = json.dumps(manifest, indent=2) + "\n"
    out = Path(args.out)
    if out.exists():
        sys.exit(f"{out} already exists; the split is frozen — do not overwrite.")
    out.write_text(text)
    print(text)
    print("sha256:", hashlib.sha256(text.encode()).hexdigest())
    # sanity checks
    assert not (set(manifest["dev"]) & set(manifest["test"]))
    assert len(manifest["dev"]) + len(manifest["test"]) == len(ids)


if __name__ == "__main__":
    main()
