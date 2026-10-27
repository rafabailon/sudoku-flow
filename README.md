# Sudoku Flow

**Sudoku Flow** is a dependency-free Python 3.10+ Sudoku solver and command-line tool. It accepts 9x9 matrices or 81-cell strings, validates givens, and solves using bit-mask constraints, naked and hidden single propagation, and Minimum Remaining Values (MRV) backtracking. It can also count solutions to check whether a puzzle has a unique answer.

## Highlights

Sudoku Flow validates shapes, characters, cell values, and duplicate clues strictly. The solver uses fast bit-mask constraint checks and incremental candidate propagation, branches with MRV, and records assignments on a trail for efficient backtracking. Invalid input, unsolvable input, and non-unique input produce distinct errors and exit codes. Solution counting stops at a requested limit, including a one-command uniqueness check, and JSON output includes the solved grid, a formatted grid, and search metrics. The project has no third-party runtime or test dependencies because `unittest` is built in.

## Requirements

Sudoku Flow needs Python 3.10 or newer. No third-party packages are required to run or test the project.

## Install

Run directly from a checkout:

```sh
PYTHONPATH=src python3 -m sudoku_flow --example
```

Or install the `sudoku-flow` command locally:

```sh
python3 -m pip install -e .
sudoku-flow --example
```

Check the version with `sudoku-flow --version`.

## Project layout

All source modules live directly in `src/`, and there is no nested `src/sudoku_flow/` package. `src/sudoku_flow.py` is the public facade that re-exports the API and version while keeping both `from sudoku_flow import ...` and `python -m sudoku_flow` working. `src/cli.py` contains the command-line interface, `src/solver.py` contains parsing, validation, solving, and solution counting, and `src/_version.py` is the single source of truth for the version. Tests live in `tests/` as `test_solver.py`, `test_cli.py`, and `run_benchmarks.py`. The package metadata is in `pyproject.toml`, and the `Makefile` provides the common test, benchmark, example, solve, uniqueness, and clean tasks.

## Usage

Solve the included difficult AI Escargot example:

```sh
python3 -m sudoku_flow --example
```

The output is JSON containing the solved grid, a human-readable rendering, elapsed time, search nodes, backtracks, and assignments.

Solve a custom puzzle from a file:

```sh
python3 -m sudoku_flow --input puzzle.txt
```

Read from standard input, either implicitly or explicitly with `-`:

```sh
cat puzzle.txt | python3 -m sudoku_flow
python3 -m sudoku_flow --input - < puzzle.txt
```

Text input may contain whitespace and line breaks. Use digits `1`-`9` for clues and `0` or `.` for empty cells. JSON input may be a 9x9 matrix or an object with a `grid` key:

```json
{"grid": [[5, 3, 0, 0, 7, 0, 0, 0, 0], [6, 0, 0, 1, 9, 5, 0, 0, 0], [0, 9, 8, 0, 0, 0, 0, 6, 0], [8, 0, 0, 0, 6, 0, 0, 0, 3], [4, 0, 0, 8, 0, 3, 0, 0, 1], [7, 0, 0, 0, 2, 0, 0, 0, 6], [0, 6, 0, 0, 0, 0, 2, 8, 0], [0, 0, 0, 4, 1, 9, 0, 0, 5], [0, 0, 0, 0, 8, 0, 0, 7, 9]]}
```

### Count solutions and check uniqueness

Count up to three solutions:

```sh
python3 -m sudoku_flow --input puzzle.txt --count 3
```

Check whether the puzzle has exactly one solution:

```sh
python3 -m sudoku_flow --input puzzle.txt --check-unique
```

Counting stops at the requested limit. In the JSON response, `exact` is `true` when the search finished below the limit, so `solution_count` is the complete count. When `exact` is `false`, the board has at least `limit` solutions.

### Exit status

Exit status `0` means a solution was found or counting completed with at least one solution. Exit status `1` means the input is malformed, contradictory, unreadable, or not a Sudoku board. Exit status `2` means the clues are valid but have no solution. Exit status `3` means `--check-unique` found more than one solution.

## Python API

After installing the package, or with `src/` on `PYTHONPATH`:

```python
from sudoku_flow import count_solutions, has_unique_solution, solve

puzzle = "530070000600195000098000060800060003400803001700020006060000280000419005000080079"
result = solve(puzzle)
print(result.grid)
print(result.stats)
print("unique:", has_unique_solution(puzzle))
print("first two solutions:", count_solutions(puzzle, limit=2))
```

`solve(board)` returns a `SudokuSolution` with an immutable tuple-of-rows grid and `SolverStats` containing elapsed seconds, search nodes, backtracks, and assignments. `count_solutions(board, limit=2)` returns the number found and stops at `limit`; it returns `0` for a valid but unsolvable board and raises `InvalidSudokuError` for malformed input. `has_unique_solution(board)` returns `True` only when exactly one solution exists. The solver does not mutate its input. Malformed input raises `InvalidSudokuError`, and a valid board without a solution raises `UnsolvableSudokuError`.

## Algorithm and validation

Row, column, and box occupancy use nine-bit integer masks, and candidate masks are updated incrementally as cells are assigned. Contradictory clues are detected before search. Propagation repeatedly fills naked singles and hidden singles, and branching uses MRV to choose the unfilled cell with the fewest candidates. Assignments are recorded on a trail, which makes backtracking local and robust, and search depth is at most 81 because the Sudoku state space is finite. Invalid input, valid-but-unsolvable puzzles, and non-unique puzzles are reported separately. By default `solve()` returns the first solution, so use `count_solutions()` or `--check-unique` when uniqueness matters.

## Tests and benchmarks

Run the checks with:

```sh
make test
make benchmark
```

The suite covers easy, difficult, sparse, empty, randomized, malformed, and unsolvable boards, text and matrix formats, non-mutation, solution counting and uniqueness, CLI file, JSON, and standard input, and CLI exit statuses. Benchmarks emit JSON timing and search metrics for easy, AI Escargot, and empty grids, including a uniqueness-counting measurement. Each case is repeated five times and the median is reported. Timings vary by machine and are informational, not performance guarantees.

## Limitations

The solver handles the standard 9x9 Sudoku rules. It does not implement variants such as diagonal, killer, or non-square grids. Extremely pathological puzzles can still require substantial backtracking, although propagation and MRV keep practical puzzles fast. The solver returns a valid solution for any solvable board; uniqueness is only established when explicitly requested.
