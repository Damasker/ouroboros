# Milestone 9 Plan — Blanket, Campaigns, Snapshot Server

## Goals

1. **Neutron / blanket channel** — dynamic thermal blanket bin with leakage, coolant extraction, optional TBR stub.
2. **Parametric campaign runner** — sweep YAML → many runs → summary table.
3. **HTTP snapshot server** — read-only JSON/JSONL API for 3D clients (stdlib only).

## Blanket energy identity

When `blanket.enabled`:

- Fraction \(f_{\mathrm{capture}}\) of neutron power enters blanket thermal energy \(E_b\).
- Fraction \(f_{\mathrm{leak}}=1-f_{\mathrm{capture}}\) leaves immediately (loss).
- Coolant extracts \(P_{\mathrm{cool}}=E_b/\tau_{\mathrm{cool}}\) (output).
- State energy includes \(E_b\); ledger residual uses capture/leak/extract instead of dumping all neutrons as instant output.

When disabled: legacy instant neutron→blanket-output accounting (v1–v8).

## Non-goals

- Full neutronics / Monte Carlo
- Authentication on HTTP server
- Distributed campaign orchestration
