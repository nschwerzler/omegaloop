#!/usr/bin/env python3
"""
OmegaLoop Eval Runner — tests skill behavior.

Type detection evals run without an LLM (pure Python).
Behavioral evals require claude CLI.

Usage:
    python tests/evals/run_evals.py                  # run all
    python tests/evals/run_evals.py --eval types     # type detection only
    python tests/evals/run_evals.py --dry-run        # show without executing
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from orchestrator.daemon import infer_loop_type


def run_type_detection_evals():
    """Test that infer_loop_type correctly classifies prompts."""
    eval_path = Path(__file__).parent / "eval_prompts.json"
    evals = json.loads(eval_path.read_text())

    passed = 0
    failed = 0
    failures = []

    for i, ev in enumerate(evals, 1):
        prompt = ev["prompt"]
        expected = ev["expected_type"]
        actual = infer_loop_type(prompt)

        if actual == expected:
            passed += 1
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
            failures.append((i, prompt[:60], expected, actual))

        print(f"  {status} [{actual:>8}] {prompt[:70]}")

    print(f"\nType Detection: {passed}/{passed + failed} passed")

    if failures:
        print("\nFailures:")
        for num, prompt, expected, actual in failures:
            print(f"  #{num}: expected={expected}, got={actual}")
            print(f"       \"{prompt}...\"")

    return failed == 0


def run_all_evals(dry_run=False):
    """Run all eval suites."""
    print("=" * 60)
    print("OmegaLoop Eval Suite")
    print("=" * 60)

    all_pass = True

    # Type detection (no LLM needed)
    print("\n--- Type Detection Evals ---")
    if not run_type_detection_evals():
        all_pass = False

    # Behavioral evals would go here (require LLM)
    if not dry_run:
        print("\n--- Behavioral Evals ---")
        print("  (Behavioral evals require claude CLI. Skipping in unit mode.)")
        print("  Run with: claude -p 'Read SKILL.md and run a converge loop on this test repo'")

    print("\n" + "=" * 60)
    if all_pass:
        print("ALL EVALS PASSED")
    else:
        print("SOME EVALS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmegaLoop Eval Runner")
    parser.add_argument("--eval", choices=["types", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.eval == "types":
        run_type_detection_evals()
    else:
        run_all_evals(dry_run=args.dry_run)
