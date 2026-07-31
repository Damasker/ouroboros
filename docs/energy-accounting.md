# Energy Accounting

## Purpose

The `EnergyLedger` is the primary scientific integrity mechanism. It must make creation or destruction of energy by coding error visible.

## Channels (joules, cumulative unless noted)

| Channel | Direction | Notes |
|---------|-----------|-------|
| `E_external_input` | input | Integrated external heating |
| `E_fusion_total` | input (nuclear) | Full 17.6 MeV × reactions |
| `E_alpha_to_plasma` | internal transfer | Subset of fusion → plasma |
| `E_neutron_blanket` | output path | Legacy instant neutron→blanket sink when `blanket.enabled=false` |
| `E_blanket` | state | Dynamic blanket thermal energy (Milestone 9) |
| `E_neutron_leaked` | loss | Immediate neutron leakage when dynamic blanket on |
| `E_coolant_extracted` | output | Coolant extraction from blanket thermal bin |
| `E_neutron_produced` | accounting | Integrated neutron fusion energy (not a residual sink when dynamic) |
| `E_magnetic` | state | \(\sum \tfrac12 L I^2\) |
| `E_internal_plasma` | state | Thermal energy all zones |
| `E_kinetic_flow` | state | \(\sum \tfrac12 M_{\mathrm{eff}} v^2\) |
| `E_recovered` | input credit | Recovered exhaust fraction |
| `E_radiation` | loss | Bremsstrahlung etc. |
| `E_wall` | loss | Wall heat load |
| `E_exhaust` | loss/output | Leaving system before recovery |
| `E_magnetic_loss` | loss | Ohmic / quench dump |
| `E_transport` | loss | Cross-field / phenomenological transport |
| `E_friction` | loss | Mechanical friction work \(\int b v^2\,dt\) |
| `E_drive_work` | input | Mechanical work of external drive forces \(\int F_{\mathrm{drive}} v\,dt\) |
| `E_error` | residual | Closure defect |

## Closure identity (per accepted step / interval)

\[
\Delta E_{\mathrm{error}}
= E_{\mathrm{state}}(t_0)
+ \int_{t_0}^{t} P_{\mathrm{in}}\,dt
+ \int_{t_0}^{t} P_{\mathrm{fusion}}\,dt
- E_{\mathrm{state}}(t)
- \int_{t_0}^{t} P_{\mathrm{out}}\,dt
- \int_{t_0}^{t} P_{\mathrm{loss}}\,dt
\]

where \(E_{\mathrm{state}} = E_{\mathrm{internal}} + E_{\mathrm{kinetic}} + E_{\mathrm{magnetic}} + E_{\mathrm{blanket}}\) (blanket term is zero when the dynamic channel is disabled).

### Dynamic blanket (Milestone 9)

When `blanket.enabled`:

- Fraction \(f_{\mathrm{capture}}\) of neutron power deposits in \(E_{\mathrm{blanket}}\).
- Leak \(1-f_{\mathrm{capture}}\) is an immediate loss.
- Coolant extracts \(P_{\mathrm{cool}}=E_{\mathrm{blanket}}/\tau_{\mathrm{cool}}\) (output).
- Residual sinks use leak + coolant (not the full produced neutron energy).

When disabled: legacy instant neutron→`E_neutron_blanket` output (v1–v8 behaviour).

## Policy

- Soft mode: log warning, mark samples `energy_trusted=false`.
- Strict mode: raise `EnergyBalanceError` and stop.
- Default relative tolerance: configurable (`energy.relative_tolerance`, default `1e-4`).
- Absolute floor avoids division blow-ups on near-zero energy systems.

## Magnetic ohmic and phenomenological coupling

- Coil ohmic power \(I^2R\) reduces \(\tfrac12 L I^2\) through the RL equation and is accumulated as `e_magnetic_loss_j`. It **is** included in the residual identity once.
- Mutual inductance \(M\) together with an independent magnetic force coefficient is **phenomenological**. Mechanical work \(F_{\mathrm{mag}} v\) and inductive power need not cancel exactly; any defect appears in \(\Delta E_{\mathrm{error}}\) and must not be hidden.
- Passive conservation tests set \(M=0\) and magnetic force coupling to zero so residual checks isolate bookkeeping errors from model inconsistency.
