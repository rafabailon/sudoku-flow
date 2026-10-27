"""Run representative Sudoku workloads and emit reproducible JSON metrics.

Each case is repeated a few times and the median timing is reported so that a
single noisy measurement does not dominate the result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sudoku_flow import count_solutions, solve

REPEATS = 5

EASY = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)

HARD = (
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

EMPTY = "." * 81


def main() -> int:
    report: list[dict[str, int | float | str | bool]] = []
    for name, puzzle in (
        ("easy", EASY),
        ("hard-ai-escargot", HARD),
        ("empty-grid", EMPTY),
    ):
        solve_times: list[float] = []
        solve_walls: list[float] = []
        count_times: list[float] = []
        counts: set[int] = set()
        solution = None

        for _ in range(REPEATS):
            started = perf_counter()
            solution = solve(puzzle)
            solve_walls.append(perf_counter() - started)
            solve_times.append(solution.stats.elapsed_seconds)

            count_started = perf_counter()
            counts.add(count_solutions(puzzle, limit=2))
            count_times.append(perf_counter() - count_started)

        assert solution is not None
        assert len(counts) == 1
        solution_count = counts.pop()

        report.append(
            {
                "case": name,
                "repeats": REPEATS,
                "solver_seconds": median(solve_times),
                "solver_wall_seconds": median(solve_walls),
                "search_nodes": solution.stats.search_nodes,
                "backtracks": solution.stats.backtracks,
                "assignments": solution.stats.assignments,
                "count_seconds": median(count_times),
                "solution_count_up_to_2": solution_count,
                "unique": solution_count == 1,
                "status": "PASS",
            }
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
