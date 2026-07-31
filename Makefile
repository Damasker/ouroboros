.PHONY: setup test lint typecheck run-scenario visualize report campaign serve demo geometry clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
SCENARIO ?= passive
RUN ?=
CAMPAIGN ?= configs/campaigns/heater_sweep.yaml
HOST ?= 127.0.0.1
PORT ?= 8765

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

campaign:
	$(PYTHON) -m ouroboros.cli --root . campaign --campaign $(CAMPAIGN)

serve:
	$(PYTHON) -m ouroboros.cli --root . serve --host $(HOST) --port $(PORT)

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
	$(MAKE) run-scenario SCENARIO=oned-passive
	$(MAKE) visualize RUN=oned-passive
	$(MAKE) run-scenario SCENARIO=coupled-consistent
	$(MAKE) visualize RUN=coupled-consistent
	$(MAKE) run-scenario SCENARIO=dt-blanket
	$(MAKE) report RUN=dt-blanket
	$(MAKE) run-scenario SCENARIO=reduced-mhd
	$(MAKE) report RUN=reduced-mhd
	$(MAKE) run-scenario SCENARIO=oned-cell-momentum
	$(MAKE) run-scenario SCENARIO=oned-cell-velocity

geometry:
	$(PYTHON) -c "from ouroboros.geometry import default_loop_geometry; default_loop_geometry().save('geometry/loop_geometry.json')"

clean:
	rm -rf results/* .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
