# Milestone 13 Plan — Magnetic nozzle / thrust channel

## Goals

1. **Magnetic nozzle module** — divert plasma from the expansion zone (or chamber proxy in lumped)
   into a directed exhaust with phenomenological efficiency.
2. **Energy closure** — extracted internal energy splits into jet power (`e_thrust_j`) and waste
   (added to exhaust channel).
3. **Metrics** — thrust [N], I_sp [s], mass flow, jet power in time series.
4. Demo config `magnetic_nozzle`.

## Non-goals

- Real MHD nozzle / de Laval design
- Open-system spacecraft trajectory integration
- Changing closed-loop geometry topology beyond a sink term

## Classification

All nozzle coefficients are **phenomenological / speculative** — not a propulsion performance claim.
