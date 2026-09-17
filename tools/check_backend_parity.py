#!/usr/bin/env python3
"""Development tool to check native/CLI phoneme parity.

Uses Phonodist to classify mismatches when they occur.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from espeakng_runtime import EspeakRuntime


def main() -> int:
    parser = argparse.ArgumentParser(description="Check native/CLI phoneme parity for a word list.")
    parser.add_argument("--voice", default="en-us", help="Voice to use (default: en-us)")
    parser.add_argument(
        "--tie",
        choices=["zwj", "none"],
        default="zwj",
        help="Tie mode: zwj for U+200D, none for no tie (default: zwj)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Input file with one word per line (default: built-in corpus)",
    )
    parser.add_argument("--separator", default=None, help="Separator character (overrides tie)")
    args = parser.parse_args()

    # Determine tie settings
    use_tie = args.tie == "zwj"
    tie_char = "\u200d" if use_tie else "\u0361"

    kwargs = {
        "voice": args.voice,
        "use_tie": use_tie,
        "tie_char": tie_char,
    }
    if args.separator:
        kwargs["separator"] = args.separator
        kwargs["use_tie"] = False

    # Load word list
    if args.input:
        words = [
            line.strip()
            for line in args.input.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        words = [
            "the",
            "and",
            "to",
            "for",
            "of",
            "we",
            "you",
            "they",
            "I'm",
            "we're",
            "you're",
            "they're",
            "we've",
            "you've",
            "we'll",
            "you'll",
            "he's",
            "she's",
            "it's",
            "hello",
            "world",
        ]

    if not words:
        print("No words to check.")
        return 0

    # Check availability
    from espeakng_runtime.discovery import maybe_find_executable, select_native

    if maybe_find_executable() is None:
        print("ERROR: eSpeak CLI not found.", file=sys.stderr)
        return 1
    if select_native()[0] is None:
        print("ERROR: Native eSpeak library not found.", file=sys.stderr)
        return 1

    # Run comparison
    try:
        from phonodist import PhonodistError, compare_pronunciations
    except ImportError:
        compare_pronunciations = None
        PhonodistError = Exception  # type: ignore[misc,assignment]

    exact = 0
    notation_only = 0
    stress_only = 0
    segmental = 0
    other = 0

    with EspeakRuntime(mode="native") as native_rt, EspeakRuntime(mode="cli") as cli_rt:
        for word in words:
            try:
                native_val = native_rt.phonemize(word, **kwargs)
                cli_val = cli_rt.phonemize(word, **kwargs)
            except Exception as e:
                print(f"ERROR on {word!r}: {e}", file=sys.stderr)
                continue

            if native_val == cli_val:
                exact += 1
                continue

            # Classify mismatch
            classification = "unknown"
            if compare_pronunciations is not None:
                try:
                    comparison = compare_pronunciations(native_val, cli_val)
                    classification = comparison.classification
                except (PhonodistError, Exception):
                    pass

            if classification == "notation_only":
                notation_only += 1
            elif classification == "stress_only":
                stress_only += 1
            elif classification == "segmental":
                segmental += 1
            else:
                other += 1

            print(f"{word}")
            print(f"  native: {native_val}")
            print(f"  cli:    {cli_val}")
            print(f"  class:  {classification}")

    # Summary
    print()
    print(f"checked:                    {len(words)}")
    print(f"exact:                      {exact}")
    print(f"notation_only mismatches:   {notation_only}")
    print(f"stress_only mismatches:     {stress_only}")
    print(f"segmental mismatches:       {segmental}")
    print(f"other mismatches:           {other}")

    return 0 if (stress_only + segmental + other) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
