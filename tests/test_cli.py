from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sudoku_flow import __version__

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"

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

UNSOLVABLE = (
    "120007090"
    "030020008"
    "009600500"
    "005300900"
    "010080002"
    "600004000"
    "300000010"
    "040000007"
    "007000300"
)


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(SRC), environment.get("PYTHONPATH", "")))
    )
    return subprocess.run(
        [sys.executable, "-m", "sudoku_flow", *args],
        cwd=PROJECT_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


class CommandLineTests(unittest.TestCase):
    def test_reports_package_version(self) -> None:
        result = run_cli("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"sudoku-flow {__version__}")

    def test_example_emits_solution_and_metrics(self) -> None:
        result = run_cli("--example")

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(len(output["grid"]), 9)
        self.assertIn("formatted_grid", output)
        self.assertIn("search_nodes", output["stats"])
        self.assertGreater(output["stats"]["assignments"], 0)

    def test_reads_puzzle_from_file_as_text_or_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sudoku.txt"
            path.write_text(EASY, encoding="utf-8")
            text_result = run_cli("--input", str(path))

            matrix = [[0] * 9 for _ in range(9)]
            path = Path(directory) / "sudoku.json"
            path.write_text(json.dumps(matrix), encoding="utf-8")
            matrix_result = run_cli("--input", str(path))

            wrapped = Path(directory) / "wrapped.json"
            wrapped.write_text(json.dumps({"grid": matrix}), encoding="utf-8")
            wrapped_result = run_cli("--input", str(wrapped))

        for result in (text_result, matrix_result, wrapped_result):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["grid"]), 9)

    def test_reads_puzzle_from_standard_input_with_and_without_dash(self) -> None:
        implicit = run_cli(stdin="." * 81)
        explicit = run_cli("--input", "-", stdin="." * 81)

        for result in (implicit, explicit):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(json.loads(result.stdout)["grid"]), 9)

    def test_reports_invalid_and_unsolvable_inputs_with_distinct_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sudoku.txt"
            path.write_text("bad", encoding="utf-8")
            invalid = run_cli("--input", str(path))
            path.write_text(UNSOLVABLE, encoding="utf-8")
            impossible = run_cli("--input", str(path))
            missing = run_cli("--input", str(Path(directory) / "missing.txt"))

        self.assertEqual(invalid.returncode, 1)
        self.assertIn("Invalid input:", invalid.stderr)
        self.assertEqual(impossible.returncode, 2)
        self.assertIn("No solution:", impossible.stderr)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("Invalid input:", missing.stderr)

    def test_count_reports_solution_count_and_exactness(self) -> None:
        unique = run_cli("--example", "--count", "2")
        multiple = run_cli("--count", "2", stdin="." * 81)

        self.assertEqual(unique.returncode, 0, unique.stderr)
        unique_output = json.loads(unique.stdout)
        self.assertEqual(unique_output["solution_count"], 1)
        self.assertTrue(unique_output["unique"])
        self.assertTrue(unique_output["exact"])

        self.assertEqual(multiple.returncode, 0, multiple.stderr)
        multiple_output = json.loads(multiple.stdout)
        self.assertEqual(multiple_output["solution_count"], 2)
        self.assertFalse(multiple_output["unique"])
        self.assertFalse(multiple_output["exact"])

    def test_check_unique_uses_dedicated_exit_status(self) -> None:
        unique = run_cli("--example", "--check-unique")
        multiple = run_cli("--check-unique", stdin="." * 81)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sudoku.txt"
            path.write_text(UNSOLVABLE, encoding="utf-8")
            impossible = run_cli("--input", str(path), "--check-unique")

        self.assertEqual(unique.returncode, 0, unique.stderr)
        self.assertTrue(json.loads(unique.stdout)["unique"])
        self.assertEqual(multiple.returncode, 3)
        self.assertFalse(json.loads(multiple.stdout)["unique"])
        self.assertEqual(impossible.returncode, 2)
        self.assertEqual(json.loads(impossible.stdout)["solution_count"], 0)

    def test_rejects_non_positive_count_limit(self) -> None:
        result = run_cli("--example", "--count", "0")

        self.assertEqual(result.returncode, 2)
        self.assertIn("positive integer", result.stderr)


if __name__ == "__main__":
    unittest.main()
