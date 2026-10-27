"""Validated Sudoku solver using bit masks, constraint propagation and MRV."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Sequence

Grid = tuple[tuple[int, ...], ...]

SIZE = 9
BOX_SIZE = 3
CELL_COUNT = SIZE * SIZE
FULL_MASK = (1 << SIZE) - 1

_DIGITS = tuple(1 << index for index in range(SIZE))
_DIGIT_VALUES = {1 << index: index + 1 for index in range(SIZE)}
_COORDINATES = tuple(divmod(index, SIZE) for index in range(CELL_COUNT))
_BOX_OF = tuple(
    (row // BOX_SIZE) * BOX_SIZE + column // BOX_SIZE
    for row, column in _COORDINATES
)

_ROWS = tuple(
    tuple(row * SIZE + column for column in range(SIZE)) for row in range(SIZE)
)
_COLUMNS = tuple(
    tuple(row * SIZE + column for row in range(SIZE)) for column in range(SIZE)
)
_BOXES = tuple(
    tuple(
        (box_row * BOX_SIZE + row_offset) * SIZE
        + box_column * BOX_SIZE
        + column_offset
        for row_offset in range(BOX_SIZE)
        for column_offset in range(BOX_SIZE)
    )
    for box_row in range(BOX_SIZE)
    for box_column in range(BOX_SIZE)
)
_UNITS = _ROWS + _COLUMNS + _BOXES


def _build_peers(index: int) -> tuple[int, ...]:
    row, column = _COORDINATES[index]
    peers = set(_ROWS[row]) | set(_COLUMNS[column]) | set(_BOXES[_BOX_OF[index]])
    peers.discard(index)
    return tuple(sorted(peers))


_PEERS = tuple(_build_peers(index) for index in range(CELL_COUNT))


class SudokuError(ValueError):
    """Base class for invalid or unsolvable Sudoku inputs."""


class InvalidSudokuError(SudokuError):
    """Raised when the input shape, values, or given clues are invalid."""


class UnsolvableSudokuError(SudokuError):
    """Raised when a valid set of clues has no solution."""


@dataclass(frozen=True, slots=True)
class SolverStats:
    """Search statistics for a successful solve."""

    elapsed_seconds: float
    search_nodes: int
    backtracks: int
    assignments: int


@dataclass(frozen=True, slots=True)
class SudokuSolution:
    """Solved 9x9 grid and its search statistics."""

    grid: Grid
    stats: SolverStats


def parse_board(board: object) -> tuple[int, ...]:
    """Parse a 9x9 matrix or 81-character digit/dot string into a flat grid."""
    if isinstance(board, str):
        cells = [character for character in board if not character.isspace()]
        if len(cells) != CELL_COUNT:
            raise InvalidSudokuError(
                f"Board text must contain exactly {CELL_COUNT} cells; got {len(cells)}."
            )
        values: list[int] = []
        for index, character in enumerate(cells):
            if character == ".":
                values.append(0)
            elif character in "0123456789":
                values.append(ord(character) - ord("0"))
            else:
                raise InvalidSudokuError(
                    f"Invalid character {character!r} at cell {index + 1}; "
                    "use digits 0-9 or '.'."
                )
        return tuple(values)

    if isinstance(board, (bytes, bytearray)) or not isinstance(board, Sequence):
        raise InvalidSudokuError(
            f"Board must be a {CELL_COUNT}-character string or a 9x9 matrix."
        )
    if len(board) != SIZE:
        raise InvalidSudokuError(f"Board matrix must have 9 rows; got {len(board)}.")

    values = []
    for row_index, row in enumerate(board):
        if isinstance(row, (str, bytes, bytearray)) or not isinstance(row, Sequence):
            raise InvalidSudokuError(
                f"Row {row_index + 1} must contain 9 integer cells."
            )
        if len(row) != SIZE:
            raise InvalidSudokuError(
                f"Row {row_index + 1} must contain 9 cells; got {len(row)}."
            )
        for column_index, value in enumerate(row):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 9
            ):
                raise InvalidSudokuError(
                    f"Cell ({row_index + 1}, {column_index + 1}) "
                    "must be an integer from 0 to 9."
                )
            values.append(value)
    return tuple(values)


def _make_masks(
    cells: Sequence[int],
) -> tuple[list[int], list[int], list[int]]:
    """Build row, column and box masks, rejecting duplicate givens."""
    row_masks = [0] * SIZE
    column_masks = [0] * SIZE
    box_masks = [0] * SIZE

    for index, value in enumerate(cells):
        if value == 0:
            continue
        bit = _DIGITS[value - 1]
        row, column = _COORDINATES[index]
        box = _BOX_OF[index]
        if row_masks[row] & bit:
            raise InvalidSudokuError(f"Duplicate clue {value} in row {row + 1}.")
        if column_masks[column] & bit:
            raise InvalidSudokuError(f"Duplicate clue {value} in column {column + 1}.")
        if box_masks[box] & bit:
            raise InvalidSudokuError(
                f"Duplicate clue {value} in 3x3 box "
                f"({box // BOX_SIZE + 1}, {box % BOX_SIZE + 1})."
            )
        row_masks[row] |= bit
        column_masks[column] |= bit
        box_masks[box] |= bit

    return row_masks, column_masks, box_masks


class _SearchEngine:
    """Incremental search state shared by one-shot solving and solution counting.

    Candidate masks are maintained as assignments are made, so propagation only
    needs to inspect the affected cells instead of rebuilding all candidates.
    A trail records assignments for cheap backtracking.
    """

    __slots__ = (
        "cells",
        "row_masks",
        "column_masks",
        "box_masks",
        "candidates",
        "trail",
        "solutions",
        "limit",
        "search_nodes",
        "backtracks",
        "assignments",
    )

    def __init__(
        self,
        cells: Sequence[int],
        row_masks: list[int],
        column_masks: list[int],
        box_masks: list[int],
        limit: int,
    ) -> None:
        self.cells = list(cells)
        self.row_masks = row_masks[:]
        self.column_masks = column_masks[:]
        self.box_masks = box_masks[:]
        self.candidates = [0] * CELL_COUNT
        self.trail: list[tuple[int, int]] = []
        self.solutions: list[Grid] = []
        self.limit = limit
        self.search_nodes = 0
        self.backtracks = 0
        self.assignments = 0
        self._recompute_candidates()

    def _candidate_mask(self, index: int) -> int:
        row, column = _COORDINATES[index]
        box = _BOX_OF[index]
        return FULL_MASK & ~(
            self.row_masks[row] | self.column_masks[column] | self.box_masks[box]
        )

    def _recompute_candidates(self) -> None:
        for index, value in enumerate(self.cells):
            self.candidates[index] = 0 if value else self._candidate_mask(index)

    def _assign(self, index: int, bit: int) -> None:
        row, column = _COORDINATES[index]
        box = _BOX_OF[index]
        self.cells[index] = _DIGIT_VALUES[bit]
        self.row_masks[row] |= bit
        self.column_masks[column] |= bit
        self.box_masks[box] |= bit
        self.candidates[index] = 0
        self.trail.append((index, bit))
        self.assignments += 1

        for peer in _PEERS[index]:
            if self.cells[peer] == 0:
                self.candidates[peer] &= ~bit

    def _rollback(self, marker: int) -> None:
        if len(self.trail) == marker:
            return
        while len(self.trail) > marker:
            index, bit = self.trail.pop()
            row, column = _COORDINATES[index]
            box = _BOX_OF[index]
            self.cells[index] = 0
            self.row_masks[row] &= ~bit
            self.column_masks[column] &= ~bit
            self.box_masks[box] &= ~bit
        self._recompute_candidates()

    def _propagate(self) -> bool:
        """Fill forced cells; return False when a contradiction is reached."""
        while True:
            changed = False

            for index, value in enumerate(self.cells):
                if value:
                    continue
                mask = self.candidates[index]
                if mask == 0:
                    return False
                if mask & (mask - 1) == 0:
                    self._assign(index, mask)
                    changed = True
            if changed:
                continue

            for unit in _UNITS:
                used = 0
                for index in unit:
                    value = self.cells[index]
                    if value:
                        used |= _DIGITS[value - 1]
                missing = FULL_MASK & ~used
                while missing:
                    bit = missing & -missing
                    missing ^= bit
                    target = -1
                    for index in unit:
                        if self.cells[index] == 0 and self.candidates[index] & bit:
                            if target != -1:
                                target = -2
                                break
                            target = index
                    if target == -1:
                        return False
                    if target >= 0:
                        self._assign(target, bit)
                        changed = True
                        break
                if changed:
                    break

            if not changed:
                return True

    def _grid(self) -> Grid:
        return tuple(
            tuple(self.cells[row * SIZE : (row + 1) * SIZE]) for row in range(SIZE)
        )

    def _search(self) -> bool:
        """Search until the solution limit is met; True means stop searching."""
        self.search_nodes += 1
        marker = len(self.trail)

        if not self._propagate():
            self._rollback(marker)
            self.backtracks += 1
            return False

        best_index = -1
        best_mask = 0
        best_count = SIZE + 1
        for index, value in enumerate(self.cells):
            if value:
                continue
            mask = self.candidates[index]
            count = mask.bit_count()
            if count < best_count:
                best_index = index
                best_mask = mask
                best_count = count
                if count == 2:
                    break

        if best_index == -1:
            self.solutions.append(self._grid())
            self._rollback(marker)
            return len(self.solutions) >= self.limit

        while best_mask:
            bit = best_mask & -best_mask
            best_mask ^= bit
            branch_marker = len(self.trail)
            self._assign(best_index, bit)
            if self._search():
                self._rollback(branch_marker)
                self._rollback(marker)
                return True
            self._rollback(branch_marker)

        self._rollback(marker)
        self.backtracks += 1
        return False

    def run(self) -> None:
        self._search()


def _prepare(board: object, limit: int = 1) -> _SearchEngine:
    cells = list(parse_board(board))
    row_masks, column_masks, box_masks = _make_masks(cells)
    return _SearchEngine(cells, row_masks, column_masks, box_masks, limit=limit)


def solve(board: object) -> SudokuSolution:
    """Solve a Sudoku, raising a specific error for invalid or impossible boards.

    The solver uses bit masks for constant-time candidate checks, propagates
    naked and hidden singles, then branches on the unfilled cell with the
    fewest candidates (MRV). Input data is never modified.
    """
    started = perf_counter()
    engine = _prepare(board)
    engine.run()

    if not engine.solutions:
        raise UnsolvableSudokuError("The given clues do not admit a Sudoku solution.")

    stats = SolverStats(
        elapsed_seconds=perf_counter() - started,
        search_nodes=engine.search_nodes,
        backtracks=engine.backtracks,
        assignments=engine.assignments,
    )
    return SudokuSolution(grid=engine.solutions[0], stats=stats)


def count_solutions(board: object, limit: int = 2) -> int:
    """Count solutions, stopping after ``limit`` are found.

    ``limit`` must be a positive integer. The result is exact when it is lower
    than the limit; when it equals the limit the board has at least that many
    solutions and counting stopped early. Invalid clues raise
    :class:`InvalidSudokuError`; valid boards with no solution return ``0``.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    engine = _prepare(board, limit=limit)
    engine.run()
    return len(engine.solutions)


def has_unique_solution(board: object) -> bool:
    """Return True when the board is valid and has exactly one solution."""
    return count_solutions(board, limit=2) == 1


def format_grid(grid: Sequence[Sequence[int]]) -> str:
    """Format a 9x9 grid with 3x3 separators for terminal display."""
    lines: list[str] = []
    for row_index, row in enumerate(grid):
        if row_index and row_index % BOX_SIZE == 0:
            lines.append("------+-------+------")
        groups = [
            " ".join(str(value) for value in row[column : column + BOX_SIZE])
            for column in range(0, SIZE, BOX_SIZE)
        ]
        lines.append(" | ".join(groups))
    return "\n".join(lines)
