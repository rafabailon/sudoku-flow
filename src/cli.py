"""Command-line interface for Sudoku Flow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from _version import __version__
from solver import (
    SudokuError,
    SudokuSolution,
    UnsolvableSudokuError,
    count_solutions,
    format_grid,
    solve,
)

_HARD_EXAMPLE = (
    "100007090"
    "030020008"
    "009600500"
    "005300900"
    "010080002"
    "600004000"
    "300000010"
    "040000007"
    "007000300"
)

EXIT_SOLVED = 0
EXIT_INVALID = 1
EXIT_NO_SOLUTION = 2
EXIT_NOT_UNIQUE = 3


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not an integer") from None
    if number < 1:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


def _format_result(solution: SudokuSolution) -> dict[str, Any]:
    return {
        "grid": [list(row) for row in solution.grid],
        "formatted_grid": format_grid(solution.grid),
        "stats": {
            "elapsed_seconds": solution.stats.elapsed_seconds,
            "search_nodes": solution.stats.search_nodes,
            "backtracks": solution.stats.backtracks,
            "assignments": solution.stats.assignments,
        },
    }


def _format_count(count: int, limit: int) -> dict[str, Any]:
    return {
        "solution_count": count,
        "limit": limit,
        "has_solution": count > 0,
        "unique": count == 1,
        "exact": count < limit,
    }


def _decode_input(raw: str) -> object:
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    return decoded if isinstance(decoded, (dict, list, str)) else raw


def _read_puzzle(args: argparse.Namespace) -> object:
    if args.example:
        return _HARD_EXAMPLE

    if args.input is None or str(args.input) == "-":
        raw = sys.stdin.read()
    else:
        raw = args.input.read_text(encoding="utf-8")

    puzzle = _decode_input(raw)
    if isinstance(puzzle, dict):
        puzzle = puzzle.get("grid")
    return puzzle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sudoku-flow",
        description=(
            "Solve or analyse a 9x9 Sudoku from an 81-character string, "
            "a 9x9 JSON matrix, or standard input."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--input",
        type=Path,
        metavar="FILE",
        help="Read the puzzle from FILE; use '-' for standard input.",
    )
    source.add_argument(
        "--example",
        action="store_true",
        help="Solve the included difficult AI Escargot example.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--count",
        type=_positive_int,
        metavar="LIMIT",
        help=(
            "Count solutions, stopping after LIMIT. "
            "The count is exact when it is lower than LIMIT."
        ),
    )
    mode.add_argument(
        "--check-unique",
        action="store_true",
        help="Report whether the puzzle has exactly one solution.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        puzzle = _read_puzzle(args)

        if args.check_unique:
            count = count_solutions(puzzle, limit=2)
            print(json.dumps(_format_count(count, 2), indent=2))
            if count == 0:
                return EXIT_NO_SOLUTION
            if count > 1:
                return EXIT_NOT_UNIQUE
            return EXIT_SOLVED

        if args.count is not None:
            count = count_solutions(puzzle, limit=args.count)
            print(json.dumps(_format_count(count, args.count), indent=2))
            return EXIT_SOLVED if count else EXIT_NO_SOLUTION

        solution = solve(puzzle)
    except UnsolvableSudokuError as error:
        print(f"No solution: {error}", file=sys.stderr)
        return EXIT_NO_SOLUTION
    except (SudokuError, OSError, UnicodeDecodeError, TypeError) as error:
        print(f"Invalid input: {error}", file=sys.stderr)
        return EXIT_INVALID

    print(json.dumps(_format_result(solution), indent=2))
    return EXIT_SOLVED


if __name__ == "__main__":
    raise SystemExit(main())
