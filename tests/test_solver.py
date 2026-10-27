from __future__ import annotations

import random
import unittest

from sudoku_flow import (
    InvalidSudokuError,
    SudokuSolution,
    UnsolvableSudokuError,
    count_solutions,
    format_grid,
    has_unique_solution,
    parse_board,
    solve,
)

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

AI_ESCARGOT = (
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

AI_ESCARGOT_SOLUTION = (
    "162857493"
    "534129678"
    "789643521"
    "475312986"
    "913586742"
    "628794135"
    "356478219"
    "241935867"
    "897261354"
)

SPARSE_17_CLUES = (
    "000000010"
    "400000000"
    "020000000"
    "000050407"
    "008000300"
    "001090000"
    "300400200"
    "050100000"
    "000806000"
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


def assert_valid_solution(
    test: unittest.TestCase, original: str, solution: SudokuSolution
) -> None:
    grid = solution.grid
    expected = set(range(1, 10))
    test.assertEqual(len(grid), 9)
    test.assertTrue(all(len(row) == 9 for row in grid))
    for row in grid:
        test.assertEqual(set(row), expected)
    for column in range(9):
        test.assertEqual({grid[row][column] for row in range(9)}, expected)
    for box_row in range(0, 9, 3):
        for box_column in range(0, 9, 3):
            box = {
                grid[row][column]
                for row in range(box_row, box_row + 3)
                for column in range(box_column, box_column + 3)
            }
            test.assertEqual(box, expected)
    for index, clue in enumerate(parse_board(original)):
        if clue:
            test.assertEqual(grid[index // 9][index % 9], clue)


def _matrix(puzzle: str) -> list[list[int]]:
    cells = parse_board(puzzle)
    return [list(cells[row * 9 : (row + 1) * 9]) for row in range(9)]


class SudokuSolverTests(unittest.TestCase):
    def test_solves_easy_puzzle_from_text(self) -> None:
        solution = solve(EASY)

        assert_valid_solution(self, EASY, solution)
        self.assertGreater(solution.stats.search_nodes, 0)
        self.assertGreaterEqual(solution.stats.elapsed_seconds, 0)
        self.assertGreater(solution.stats.assignments, 0)

    def test_solves_classic_hard_ai_escargot(self) -> None:
        solution = solve(AI_ESCARGOT)

        assert_valid_solution(self, AI_ESCARGOT, solution)
        self.assertEqual(
            "".join(str(value) for row in solution.grid for value in row),
            AI_ESCARGOT_SOLUTION,
        )
        self.assertLess(solution.stats.elapsed_seconds, 5.0)

    def test_solves_sparse_17_clue_puzzle(self) -> None:
        solution = solve(SPARSE_17_CLUES)

        assert_valid_solution(self, SPARSE_17_CLUES, solution)

    def test_solves_empty_board(self) -> None:
        solution = solve("." * 81)

        assert_valid_solution(self, "." * 81, solution)

    def test_solves_matrix_input_without_mutating_it(self) -> None:
        original = _matrix(EASY)
        snapshot = [row[:] for row in original]

        solution = solve(original)

        self.assertEqual(original, snapshot)
        assert_valid_solution(self, EASY, solution)

    def test_accepts_dot_and_whitespace_formatted_text(self) -> None:
        dotted = "\n".join(
            " ".join(
                "." if digit == "0" else digit
                for digit in EASY[row * 9 : (row + 1) * 9]
            )
            for row in range(9)
        )

        self.assertEqual(parse_board(dotted), parse_board(EASY))

    def test_randomized_subsets_of_a_solution_remain_solvable(self) -> None:
        generator = random.Random(20261023)
        complete = solve("." * 81).grid
        for _ in range(8):
            puzzle = [list(row) for row in complete]
            for index in generator.sample(range(81), 58):
                puzzle[index // 9][index % 9] = 0
            solution = solve(puzzle)
            assert_valid_solution(
                self,
                "".join(str(value) for row in puzzle for value in row),
                solution,
            )

    def test_rejects_wrong_string_length_and_characters(self) -> None:
        for invalid in ("." * 80, "." * 80 + "x", "123", ""):
            with self.subTest(value=invalid):
                with self.assertRaises(InvalidSudokuError):
                    parse_board(invalid)

    def test_rejects_non_text_non_matrix_inputs(self) -> None:
        for invalid in (None, 42, b"." * 81, object()):
            with self.subTest(value=type(invalid).__name__):
                with self.assertRaises(InvalidSudokuError):
                    solve(invalid)

    def test_rejects_invalid_matrix_shapes_values_and_booleans(self) -> None:
        with self.assertRaises(InvalidSudokuError):
            solve([[0] * 9] * 8)
        malformed = [[0] * 9 for _ in range(9)]
        malformed[3] = [0] * 8
        with self.assertRaises(InvalidSudokuError):
            solve(malformed)
        for invalid_value in (True, False, -1, 10, 1.5, "1", None):
            with self.subTest(value=invalid_value):
                malformed = [[0] * 9 for _ in range(9)]
                malformed[0][0] = invalid_value
                with self.assertRaises(InvalidSudokuError):
                    solve(malformed)

    def test_rejects_duplicate_clues_in_each_constraint_group(self) -> None:
        for first, second, label in (
            (0, 1, "row"),
            (0, 9, "column"),
            (0, 10, "box"),
        ):
            with self.subTest(group=label):
                cells = ["0"] * 81
                cells[first] = cells[second] = "7"
                with self.assertRaises(InvalidSudokuError):
                    solve("".join(cells))

    def test_detects_valid_but_unsolvable_clues(self) -> None:
        with self.assertRaises(UnsolvableSudokuError):
            solve(UNSOLVABLE)

    def test_format_grid_includes_box_separators(self) -> None:
        solution = solve(EASY)
        rendered = format_grid(solution.grid)

        self.assertIn("------+-------+------", rendered)
        self.assertEqual(len(rendered.splitlines()), 11)


class SolutionCountingTests(unittest.TestCase):
    def test_known_puzzles_have_exactly_one_solution(self) -> None:
        for name, puzzle in (
            ("easy", EASY),
            ("ai-escargot", AI_ESCARGOT),
            ("sparse-17", SPARSE_17_CLUES),
        ):
            with self.subTest(puzzle=name):
                self.assertEqual(count_solutions(puzzle, limit=2), 1)
                self.assertTrue(has_unique_solution(puzzle))

    def test_empty_board_has_many_solutions_and_stops_at_limit(self) -> None:
        self.assertEqual(count_solutions("." * 81, limit=1), 1)
        self.assertEqual(count_solutions("." * 81, limit=2), 2)
        self.assertEqual(count_solutions("." * 81, limit=5), 5)
        self.assertFalse(has_unique_solution("." * 81))

    def test_unsolvable_board_has_zero_solutions(self) -> None:
        self.assertEqual(count_solutions(UNSOLVABLE, limit=2), 0)
        self.assertFalse(has_unique_solution(UNSOLVABLE))

    def test_invalid_board_raises_invalid_error(self) -> None:
        with self.assertRaises(InvalidSudokuError):
            count_solutions("." * 80)
        with self.assertRaises(InvalidSudokuError):
            count_solutions([[0] * 9] * 8)

    def test_limit_must_be_a_positive_integer(self) -> None:
        for invalid in (0, -1, 1.5, True, False, "2", None):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    count_solutions(EASY, limit=invalid)  # type: ignore[arg-type]

    def test_counting_does_not_mutate_matrix_input(self) -> None:
        original = _matrix(EASY)
        snapshot = [row[:] for row in original]

        count_solutions(original, limit=2)

        self.assertEqual(original, snapshot)


if __name__ == "__main__":
    unittest.main()
