"""Sudoku Flow: a dependency-free Sudoku solver and analysis toolkit.

The implementation lives in the flat modules next to this file. This module is
the public facade and the ``python -m sudoku_flow`` entry point, so existing
imports and commands keep working after the source reorganization.
"""

from __future__ import annotations

from _version import __version__
from cli import main
from solver import (
    Grid,
    InvalidSudokuError,
    SudokuError,
    SudokuSolution,
    SolverStats,
    UnsolvableSudokuError,
    count_solutions,
    format_grid,
    has_unique_solution,
    parse_board,
    solve,
)

__all__ = [
    "Grid",
    "InvalidSudokuError",
    "SudokuError",
    "SudokuSolution",
    "SolverStats",
    "UnsolvableSudokuError",
    "__version__",
    "count_solutions",
    "format_grid",
    "has_unique_solution",
    "main",
    "parse_board",
    "solve",
]


if __name__ == "__main__":
    raise SystemExit(main())
