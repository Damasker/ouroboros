# 3D Visualization Roadmap

## Goal

Attach full 3D visualization **without modifying Simulation Core**.

## Contract

The core already emits versioned JSONL snapshots (`snapshot_schema_version`, currently **1.1.0**) with:

- `time`
- `segments[]` — density, temperature, flow_velocity, magnetic_field, …
- `components[]` — throttle currents, stored energy, status
- optional `cells[]` — per-cell fields for `oned` model (segment averages remain in `segments`)
- optional `events[]`

Geometry is defined separately in `geometry/loop_geometry.json` (nodes, segments, radii, orientations, element types).

## Integration paths (no core changes)

1. **Browser (Three.js / WebGPU)**  
   Fetch/static-load JSONL + geometry; interpolate between frames; color by density/temperature.

2. **Godot / Unity**  
   Side-load geometry; poll file or localhost API (`GET /snapshot`); map segment IDs to meshes.

3. **Blender**  
   Python import script reads JSONL and keyframes empties/curves.

4. **ParaView**  
   Convert snapshots to VTK/XDMF via a thin adapter (future `tools/snapshot_to_vtk.py`).

5. **Native OpenGL/Vulkan**  
   Same snapshot schema; engine owns camera/materials only.

## Recommended sequence

1. Keep v1 matplotlib schematic + 2D plots.
2. Stabilize `snapshot_schema_version` and geometry IDs.
3. Add optional HTTP snapshot server (`make serve` / `ouroboros serve`) — **done in Milestone 9**.
4. Browser schematic viewer at `/viewer` — **done in Milestone 11**.
5. Prototype Three.js / WebGPU volumetric viewer consuming live snapshots.
6. Only then consider in-engine particle FX — still driven by exported fields, never by re-implementing ODEs.

## Anti-patterns

- Calling SciPy from a game engine script.
- Duplicating fusion formulas in the visualizer.
- Changing segment IDs without a schema version bump.
