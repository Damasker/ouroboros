# Milestone 8 Plan — Extended Physics

## Goals

1. **Consistent throttle–flow coupling** — electromechanical port where mechanical power and circuit EMF cancel (no ledger defect from independent \(F_{\mathrm{mag}}\) and \(M\,dI_p/dt\)).
2. **Multi-zone / 1D D–T burn demos** at numerically tractable density.
3. **Stubs**: anisotropic transport (∥/⊥) and a reduced-MHD-like magnetic pressure term (phenomenological).

## Consistent coupling model

Classification: simplified / phenomenological electromechanics.

\[
F_{\mathrm{mag}} = -k_{\mathrm{em}} I, \qquad
L\frac{dI}{dt}+R I = k_{\mathrm{em}} v
\]

Identity: \(\frac{d}{dt}(E_{\mathrm{kin}}+E_{\mathrm{mag}})=F_{\mathrm{other}}v - I^2 R\).

Config: `throttle_*.coupling_mode: none | phenomenological | consistent`.

## Status

**Complete** — see `docs/milestones/REPORT.md` (Milestone 8).
