# ADR-001: Technology Stack

**Status:** Accepted  
**Date:** 2026-07-30  
**Project:** Ouroboros Plasma Loop Simulator

## Context

The first prototype must implement a stiff-capable 0D ODE plasma-loop model with strict energy accounting, while remaining extensible to multi-zone 0D, 1D flow, MHD, particle models, and external 3D clients. The physics core must not depend on any GUI or rendering library.

## Alternatives considered

### 1. Python (NumPy / SciPy / Matplotlib)

| Criterion | Assessment |
|-----------|------------|
| Numerical modelling convenience | Excellent: rapid model iteration, rich scientific ecosystem |
| ODE libraries | `scipy.integrate.solve_ivp` (RK45, DOP853, Radau, BDF, LSODA) |
| Performance | Adequate for 0D/small multi-zone; bottlenecks later |
| Testability | Excellent (`pytest`, property testing via Hypothesis) |
| Plotting | Excellent (`matplotlib`) |
| Future 3D visualization | Indirect: export snapshots; browser/Godot/Unity consume JSON |
| Compute/UI separation | Natural via packages and file/API boundary |
| GPU portability | Possible later via Numba/CuPy/JAX; not native |
| Browser / Godot / Unity integration | Via JSON/JSONL/HDF5 snapshot protocol |

### 2. Julia

| Criterion | Assessment |
|-----------|------------|
| Numerical modelling convenience | Outstanding for scientific ODEs |
| ODE libraries | DifferentialEquations.jl (best-in-class stiff solvers) |
| Performance | Near-C without leaving the language |
| Testability | Good |
| Plotting | Good (Plots.jl, Makie.jl) |
| Future 3D visualization | Makie strong; external engines still need IPC |
| Compute/UI separation | Good |
| GPU portability | Growing (CUDA.jl) |
| Browser / engine integration | Weaker packaging/deployment for non-Julia clients |

### 3. Rust (+ ndarray / sundials) or C++

| Criterion | Assessment |
|-----------|------------|
| Numerical modelling convenience | Lower velocity for exploratory physics |
| ODE libraries | sundials, ode_solvers; more wiring required |
| Performance | Excellent |
| Testability | Strong, but slower to iterate on model equations |
| Plotting | External (Python/JS) |
| Future 3D visualization | Excellent for native OpenGL/Vulkan clients |
| Compute/UI separation | Excellent |
| GPU portability | Excellent (CUDA/Vulkan compute) |
| Browser integration | Via WASM or native IPC |

### 4. TypeScript + WebAssembly

| Criterion | Assessment |
|-----------|------------|
| Numerical modelling convenience | Moderate; fewer mature stiff ODE libraries |
| ODE libraries | Limited compared to SciPy / DiffEq.jl |
| Performance | Good with WASM; stiff solvers harder |
| Testability | Good |
| Plotting | Excellent in browser |
| Future 3D visualization | Excellent (Three.js / WebGPU) |
| Compute/UI separation | Easy to blur; must be enforced |
| GPU portability | WebGPU later |
| Engine integration | Natural for browser; weaker for ParaView/HPC |

## Decision

**Adopt Python 3.11+ for the first prototype**, with a strict package boundary:

- `ouroboros` simulation core and domain model have **no** dependency on Matplotlib, browser, or 3D engines.
- Visualization is a separate CLI/module that reads exported results only.
- Configuration and results use **YAML + JSON + CSV + JSONL snapshots** (HDF5 optional later).
- Scientific stack: NumPy, SciPy, PyYAML, Pydantic (config validation), Matplotlib (viz only), pytest, Hypothesis.

### Why Python now

1. Fastest path to a correct energy ledger, stiff ODE integration, and test coverage.
2. SciPy stiff solvers (BDF/LSODA/Radau) are sufficient for 0D coupled branch/throttle dynamics.
3. Clear separation of core vs. visualization satisfies the architectural constraint.
4. JSON/CSV export enables Godot, Unity, browser, ParaView, or a future Rust/Julia kernel without rewriting the data contract.

## Consequences / limitations

- Pure-Python RHS evaluation will not scale to fine 1D/2D MHD.
- Floating-point reproducibility across platforms is “best effort” (document SciPy/BLAS versions).
- GPU acceleration is not available out of the box.

## Migration plan when complexity grows

1. **Keep the public API and snapshot schema stable** (versioned).
2. Profile RHS and EnergyLedger; extract hot kernels to Numba or a Rust extension (`pyo3`) behind the same interfaces.
3. If multi-physics stiffness dominates, rewrite the integrator kernel in Julia or C++/sundials while Python retains orchestration, I/O, and tests.
4. Optionally expose a gRPC/REST control plane so Godot/Unity/Web clients never import the physics package.
5. Introduce HDF5/Zarr for large spatiotemporal fields when moving beyond 0D.

## Explicit non-goals of this ADR

- Claiming Python is optimal for production MHD.
- Binding the physics model to Matplotlib or any 3D engine.
