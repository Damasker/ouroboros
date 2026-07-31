# Ouroboros Plasma Loop Simulator

**Research prototype — not a demonstration that a real fusion reactor of this type works.**

0D dual-branch closed plasma-loop model with passive magnetic throttles, strict energy accounting, and an export path for future 3D clients.

## Warning

All phenomenological coefficients, placeholder drives, and speculative topology choices are documented in `docs/assumptions.md` and `docs/limitations.md`. Do not treat outputs as engineering design data.

## Architecture

Layered packages under `src/ouroboros/`:

1. **Simulation Core** — ODE system, SciPy integrator, EnergyLedger, events  
2. **Domain model** — plasma zones, throttles, chamber, config/result types  
3. **Data / API** — YAML config, CSV/JSON/JSONL export, `SimulationSession`  
4. **Visualization** — Matplotlib plots + schematic (reads exports only)

See `docs/ADR-001-technology-stack.md` and `docs/architecture.md`.

## Requirements

- Python 3.11+
- `make`, `pip`

## Setup

```bash
make setup
```

## Run tests

```bash
make test
```

## Run scenarios

```bash
make run-scenario SCENARIO=passive
make run-scenario SCENARIO=driven
make run-scenario SCENARIO=synthetic-oscillation
make run-scenario SCENARIO=dt-fusion
make run-scenario SCENARIO=multizone-passive
make run-scenario SCENARIO=multizone-driven
make run-scenario SCENARIO=oned-passive
make run-scenario SCENARIO=oned-driven
```

Fault examples: `fault-block-a`, `fault-quench`, `fault-heater-trip`, `fault-helium`, `fault-density-spike`, `fault-cooling-loss`.

## Visualize

```bash
make visualize RUN=passive
make report RUN=passive
```

## Outputs

Each run writes `results/<run-id>/`:

| File | Content |
|------|---------|
| `config.yaml` | Experiment configuration |
| `timeseries.csv` | Time series |
| `events.json` | Simulation events |
| `energy_report.json` | EnergyLedger + residual |
| `result.json` | Full machine-readable result |
| `snapshots.jsonl` | Versioned frames for 3D clients |
| `plots/` | After `make visualize` |

## Project layout

```
configs/          scenario YAML
docs/             ADR, equations, assumptions, roadmap
geometry/         spatial loop description (viz only for 0D)
src/ouroboros/    core, domain, physics, api, io, viz, controllers
tests/            unit, property, integration
```

## Example configuration (excerpt)

```yaml
simulation:
  duration_s: 0.5
  scenario: passive
fusion:
  enabled: false
losses:
  bremsstrahlung: false
  transport: false
```

## Example result fields

Time series include densities, temperatures (eV display), flows, throttle currents, fusion/α/neutron/external powers, Q, and energy residual.

## Known limitations

- 0D lumped zones only  
- Magnetic throttle ↔ flow coupling is phenomenological  
- Neutrons are an energy bin, not a blanket transport model  
- Residual may grow when mutual inductance and magnetic force coefficients are inconsistent (documented)  
- No claim of device feasibility  

## License

MIT
