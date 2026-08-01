# Limitations

1. **Not a reactor design tool.** Results must not be interpreted as evidence of engineering feasibility.
2. **0D / multi-zone 0D / simplified 1D only.** 1D uses finite-volume solvers (including HLLD) with dual-path velocities — not a full compressible MHD pipe model. No turbulence cascade, no realistic divertor physics.
3. **Phenomenological throttles.** Mutual inductance coupling to flow is a research toy model.
4. **Fixed geometry volumes.** Compression work terms are simplified or optional.
5. **Single reactivity channel (D–T).** No D–D, T–T, or advanced fuels in v1.
6. **Neutron blanket is an energy bin**, not a transport/activation calculation.
7. **No radiation transport**, no neutrals, no sheath model.
8. **Controllers are academic** (PID / slow supervisor), not plant-grade control.
9. **Numerical residuals** can appear from adaptive stepping and discrete event handling; they are measured, not hidden.
10. **Cross-platform bitwise reproducibility** is not guaranteed due to BLAS/SciPy differences.
11. **3D visualization** consumes snapshots only; it does not validate the physics.
12. **Magnetic nozzle / space-propulsion** scenarios exist as research demos (see `magnetic-nozzle` and related milestones). They are simplified nozzle+orbit toys — not thruster design or mission analysis tools.
