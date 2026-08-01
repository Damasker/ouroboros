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
make run-scenario SCENARIO=coupled-consistent
make run-scenario SCENARIO=multizone-dt
make run-scenario SCENARIO=oned-dt
make run-scenario SCENARIO=dt-blanket
make run-scenario SCENARIO=reduced-mhd
make run-scenario SCENARIO=oned-cell-momentum
make run-scenario SCENARIO=oned-cell-velocity
make run-scenario SCENARIO=magnetic-nozzle
make run-scenario SCENARIO=oned-momentum-flux
make run-scenario SCENARIO=oned-rusanov
make run-scenario SCENARIO=oned-hllc
make run-scenario SCENARIO=oned-energy-flux
make run-scenario SCENARIO=oned-hllc-energy
make run-scenario SCENARIO=oned-roe
make run-scenario SCENARIO=oned-wave-mhd
make run-scenario SCENARIO=dt-blanket-mc
make run-scenario SCENARIO=nozzle-trajectory
make run-scenario SCENARIO=oned-hlld
make run-scenario SCENARIO=dt-blanket-zones
make run-scenario SCENARIO=orbit-3dof
```

App UI (after `make serve`):

- Schematic: `http://127.0.0.1:8765/viewer`
- Volumetric WebGPU: `http://127.0.0.1:8765/viewer/webgpu.html`
- Protocol browser: `http://127.0.0.1:8765/viewer/protocol.html`

Keyboard in schematic: `Space` play/pause, `←`/`→` step frames, `F` cycle field.

**Public site:** [https://ouroboros.beart.cc](https://ouroboros.beart.cc) (GitHub Pages gallery + static data API).  
Gallery default: **18 progressive detail runs** (`detail-01` … `detail-18`, 11 → 198 cells) **plus** the five classic demos.  
Deploy notes: [docs/deploy.md](docs/deploy.md).

```bash
make publish-site DOMAIN=ouroboros.beart.cc
docker build -f Dockerfile.web -t ouroboros-web .
```

Native clients: `clients/godot/`, `clients/unity/`; protocol at `/client/protocol`, stream at `/runs/<id>/client-stream`.

Fault examples: `fault-block-a`, `fault-quench`, `fault-heater-trip`, `fault-helium`, `fault-density-spike`, `fault-cooling-loss`.

## Campaigns & snapshot server

```bash
make campaign CAMPAIGN=configs/campaigns/heater_sweep.yaml
make detail-sweep   # cells_per_segment = 1 … 18 on oned-hlld
make serve HOST=127.0.0.1 PORT=8765
```

Open the schematic viewer at `http://127.0.0.1:8765/viewer`.

HTTP endpoints (read-only): `/health`, `/viewer`, `/geometry`, `/runs`, `/runs/<id>/snapshots[/latest]`, `/energy`.

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

- Lumped / multi-zone / coarse 1D models only (not reactor design tools)
- Magnetic throttle ↔ flow coupling is phenomenological unless `coupling_mode: consistent`
- Dynamic blanket is a thermal bin + TBR stub, not neutronics transport
- Magnetic nozzle is a speculative extract→jet proxy, not a thruster design tool
- Residual may grow when mutual inductance and magnetic force coefficients are inconsistent (documented)
- No claim of device feasibility  

## License

MIT
