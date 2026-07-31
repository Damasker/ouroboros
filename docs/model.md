# Conceptual Model

## Purpose

Ouroboros is a **research** 0D simulator of a conceptual dual-branch closed plasma loop with a shared reaction chamber and passive magnetic throttles. It is **not** evidence that such a reactor is physically realizable.

## Topology

```
Branch A → Magnetic Throttle A ┐
                               ├→ Reaction Chamber → Expansion → Separator
Branch B → Magnetic Throttle B ┘                              ↓
                                                    Return Channel
                                                         ↓
                                              split → A and B
```

Branches start with a small intentional asymmetry so flow competition and oscillations can be studied.

## State (per branch / zone)

Minimum fields (SI unless noted):

- particle number `N` [1]
- density `n` [m⁻³]
- volume `V` [m³]
- flow velocity `v` [m/s]
- mass flow rate `ṁ` [kg/s]
- ion / electron temperatures `T_i`, `T_e` [K] (config may specify eV; converted on load)
- pressure `p` [Pa]
- internal energy `U` [J]
- magnetic energy `E_mag` [J]
- species fractions: D, T, He, impurities [-]
- residence time `τ_res` [s]
- confinement factor `κ_conf` [-] (phenomenological)

Shared / component state:

- throttle coil currents `I_s` [A]
- chamber energy and composition
- EnergyLedger accumulators [J]
- controller setpoints

## Operating modes

1. **Passive circulation** — fusion off, no post-startup external heat; check decay and energy conservation.
2. **Driven circulation** — controlled external power; check flow stability.
3. **Synthetic heat source** — artificial heat instead of fusion; look for limit cycles.
4. **D–T fusion model** — temperature-dependent reactivity, α-heating, neutron channel, Q.

Fault scenarios: branch blockage, cooling loss, throttle quench, density spike, heater trip, helium ash buildup, energy-balance violation.

## Geometry vs. physics

A spatial loop description (nodes, segments, radii, orientations) is maintained for visualization and for the multi-zone model.

### Models

| `simulation.model` | Description |
|--------------------|-------------|
| `lumped` (default) | Fixed A/B/chamber/return bookkeeping (`LoopSystem`) |
| `multizone` | One zone per geometry segment; exchange along loop edges (`MultiZoneSystem`) |
| `oned` | Finite-volume cells along segment centerlines (`OneDSystem`) |

For `lumped`/`multizone`, coordinates do **not** enter the RHS. For `oned`, cells are ordered along segment length and exchange via upwind fluxes; dual-path velocities \(v_a,v_b\) remain ODEs (simplified).
