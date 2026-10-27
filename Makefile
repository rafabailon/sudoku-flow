PYTHON ?= python3
export PYTHONPATH := src

.PHONY: test benchmark example solve unique clean

test:
	$(PYTHON) -m unittest discover -s tests -v

benchmark:
	$(PYTHON) tests/run_benchmarks.py

example:
	$(PYTHON) -m sudoku_flow --example

solve:
	$(PYTHON) -m sudoku_flow

unique:
	$(PYTHON) -m sudoku_flow --example --check-unique

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f \( -name '*.py[co]' -o -name '.coverage' \) -delete
	rm -rf .pytest_cache build dist .eggs src/*.egg-info *.egg-info
