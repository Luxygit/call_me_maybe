
all: install run

install:
	uv sync

run: install
	uv run python -m src

debug: install
	uv run python -m pdb src

clean:
	rm -rf __pycache__ .venv .mypy_cache dist build *.egg-info src/__pycache__ src/mypy_cache /llm_sdk/llm_sdk/__pycache__

lint:
	flake8 src/
	mypy src/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 src/
	mypy src/ --strict

.PHONY: all install run debug clean lint lint-strict
