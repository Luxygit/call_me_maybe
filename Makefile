
SRC			= src/main.py
VENV		= .venv
PYTHON		= $(VENV)/bin/python3
PIP			= $(VENV)/bin/pip3

all: install run

$(VENV):
	python3 -m venv $(VENV)
	$(PIP) install --quiet flake8 mypy

install: $(VENV)

run: install
	$(PYTHON) $(SRC)

debug: install
	$(PYTHON) -m pdb $(SRC)

clean:
	rm -rf __pycache__ .mypy_cache dist build *.egg-info $(VENV)

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

.PHONY: all install run debug clean lint lint-strict
