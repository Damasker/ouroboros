.PHONY: setup test lint typecheck run-scenario visualize report demo geometry clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
SCENARIO ?= passive
RUN ?=

setup:
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	$(PYTHON) -c "from ouroboros.geometry import default_loop_geometry; default_loop_geometry().save('geometry/loop_geometry.json')"

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests

typecheck:
	$(PYTHON) -m mypy src/ouroboros || true

run-scenario:
	$(PYTHON) -m ouroboros.cli --root . run --scenario $(SCENARIO) --run-id $(SCENARIO)

visualize:
	@if [ -z "$(RUN)" ]; then echo "Usage: make visualize RUN=<run-id>"; exit 1; fi
	$(PYTHON) -m ouroboros.cli --root . visualize --run $(RUN)

report:
	@if [ -z "$(RUN)" ]; then echo "Usage: make report RUN=<run-id>"; exit 1; fi
	$(PYTHON) -m ouroboros.cli --root . report --run $(RUN)

demo: setup
	$(MAKE) run-scenario SCENARIO=passive
	$(MAKE) visualize RUN=passive
	$(MAKE) run-scenario SCENARIO=synthetic-oscillation
	$(MAKE) visualize RUN=synthetic-oscillation
	$(MAKE) run-scenario SCENARIO=dt-fusion
	$(MAKE) visualize RUN=dt-fusion
	$(MAKE) report RUN=dt-fusion
	$(MAKE) run-scenario SCENARIO=multizone-passive
	$(MAKE) visualize RUN=multizone-passive

geometry:
	$(PYTHON) -c "from ouroboros.geometry import default_loop_geometry; default_loop_geometry().save('geometry/loop_geometry.json')"

clean:
	rm -rf results/* .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
