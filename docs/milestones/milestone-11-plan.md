# Milestone 11 Plan — Cell-pressure momentum + snapshot viewer

## Goals

1. **1D cell-pressure momentum** — optional `oned.momentum_mode: cell_pressure` that
   integrates face \(\Delta p\,A\) along each path from cell pressures (not only zone-mean
   \(\Delta p\)), with compressional kin↔int exchange for ledger closure.
2. **Browser snapshot viewer** — static HTML/JS client served by `ouroboros serve`,
   consuming `/runs`, `/runs/<id>/snapshots`, and geometry JSON.

## Non-goals

- Full cell-local velocity state vector / Riemann solvers
- Monte Carlo neutronics
- Authenticated multi-user UI
- Game-engine (Godot/Unity) client

## Classification

Cell-pressure path forces remain **simplified / phenomenological** hydrostatics mapped onto
dual-path ODEs — not a multi-dimensional momentum field.
