
SRC			= main.py
# MAP			= maps/easy/01_linear_path.txt
# MAP			= maps/easy/02_simple_fork.txt
# MAP			= maps/easy/03_basic_capacity.txt
# MAP			= maps/medium/01_dead_end_trap.txt
# MAP			= maps/medium/02_circular_loop.txt
# MAP			= maps/medium/03_priority_puzzle.txt
# MAP			= maps/hard/01_maze_nightmare.txt
# MAP			= maps/hard/02_capacity_hell.txt
 MAP			= maps/hard/03_ultimate_challenge.txt
# MAP			= maps/challenger/01_the_impossible_dream.txt
VENV		= .venv
PYTHON		= $(VENV)/bin/python3
PIP			= $(VENV)/bin/pip3

all: install run

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --quiet flake8 mypy pygame-ce

install: $(VENV)

run: install
	$(PYTHON) $(SRC) ${MAP}

debug: install
	$(PYTHON) -m pdb $(SRC) ${MAP}

clean:
	rm -rf __pycache__ .mypy_cache dist build *.egg-info $(VENV)

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

.PHONY: all install run debug clean lint lint-strict
