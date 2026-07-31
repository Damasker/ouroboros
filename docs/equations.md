# Equations (v1)

All symbols use SI unless an explicit conversion is stated. Coefficients marked **phenomenological** or **placeholder** are not validated reactor parameters.

## 0. Multi-zone network (Milestone 6)

When `simulation.model: multizone`, each geometry segment is a zone. Directed edges define exchange. Classification: simplified / phenomenological connectivity.

Volumes are role-scaled from geometric \(\pi r^2 L\) to match `geometry.*_volume_m3` totals.

## 0b. 1D finite volume (Milestone 7)

Each segment is split into \(N_c\) cells. Face particle flux (upwind):

\[
\phi_N = u_{\mathrm{eff}}\, A\, n_{\mathrm{upwind}}
\]

\[
\phi_E = \phi_N \cdot (U/N)_{\mathrm{upwind}}
\]

Classification: simplified physics. Dual-path velocities and throttles remain as in the multi-zone model. Snapshot schema **1.1.0** adds optional `cells[]` while keeping segment averages.

## 1. Particle balance (per zone)

\[
\frac{dN}{dt} = \dot{N}_{\mathrm{in}} - \dot{N}_{\mathrm{out}} - R_{\mathrm{fusion}} - R_{\mathrm{loss}} + R_{\mathrm{fuel}}
\]

| Symbol | Meaning | Units |
|--------|---------|-------|
| \(N\) | particle number | 1 |
| \(\dot{N}_{\mathrm{in/out}}\) | convective exchange | s⁻¹ |
| \(R_{\mathrm{fusion}}\) | fusion consumption rate | s⁻¹ |
| \(R_{\mathrm{loss}}\) | wall/leak loss rate | s⁻¹ |
| \(R_{\mathrm{fuel}}\) | fueling source | s⁻¹ |

Applicability: 0D well-mixed zone. Source: standard continuity bookkeeping (established accounting; exchange terms are simplified).

## 2. Energy balance (per zone)

\[
\frac{dE}{dt} = P_{\mathrm{compression}} + P_{\alpha} + P_{\mathrm{external}} + P_{\mathrm{recovered}}
- P_{\mathrm{radiation}} - P_{\mathrm{transport}} - P_{\mathrm{wall}} - P_{\mathrm{exhaust}}
\]

Powers in watts [W]. Neutron power from fusion is routed to the **blanket channel** and does **not** return to plasma internal energy in v1.

## 3. Flow dynamics (inertial lumped model)

\[
M_{\mathrm{eff}}\frac{dv}{dt} = F_{\mathrm{drive}} + F_{\mathrm{magnetic}} + F_{\mathrm{pressure}} + F_{\mathrm{friction}}
\]

| Term | Classification |
|------|----------------|
| \(M_{\mathrm{eff}}\) | phenomenological effective inertia [kg] |
| \(F_{\mathrm{drive}}\) | placeholder / external or synthetic drive [N] |
| \(F_{\mathrm{magnetic}}\) | phenomenological coupling to throttle [N] |
| \(F_{\mathrm{pressure}}\) | simplified \(\Delta p\,A\) [N] |
| \(F_{\mathrm{friction}}\) | linear drag \(-b v\) [N] |

This is **not** a derived MHD momentum equation.

## 4. Passive magnetic throttle

Inductively coupled RL form:

\[
L_s\frac{dI_s}{dt} + R_s I_s = -M\frac{dI_p}{dt}
\]

Plasma-side proxy current \(I_p \propto \dot{m}\) or \(v\) (phenomenological mapping). Superconducting mode uses very small but non-zero \(R_s\).

Limits:

- \(|I_s| \le I_{\mathrm{limit}}\)
- estimated \(B \le B_{\mathrm{limit}}\)
- quench event if limits exceeded (fault model)

Stored magnetic energy (ideal inductor proxy):

\[
E_{\mathrm{mag}} = \tfrac{1}{2} L_s I_s^2
\]

**Do not treat this as a validated magnet design model.**

## 5. D–T fusion

\[
R_f = n_D n_T \langle\sigma v\rangle V, \qquad P_f = R_f E_f, \qquad E_f = 17.6\,\mathrm{MeV}
\]

Energy partition (established nuclear data):

- α: \(3.5\,\mathrm{MeV}\) → plasma heating channel
- neutron: \(14.1\,\mathrm{MeV}\) → blanket channel (not returned to plasma in v1)

Reactivity \(\langle\sigma v\rangle\): Bosch–Hale analytic fit (H.-S. Bosch & G.M. Hale, *Nuclear Fusion* 32, 611 (1992)) implemented as `BoschHaleReactivityModel`. A `PlaceholderReactivityModel` remains available for demos.

## 6. Losses (each optional via config)

- Bremsstrahlung (simplified hydrogenic formula; impurities via \(Z_{\mathrm{eff}}\) factor) — simplified physics
- Transport \(\propto U/\tau_E\) — phenomenological
- Wall load — phenomenological
- Exhaust — phenomenological
- Magnetic system ohmic / quench dump — simplified / phenomenological
- Incomplete recovery — phenomenological
- Impurity radiation multiplier — phenomenological

## 7. Fusion gain (conditional)

\[
Q = \frac{P_{\mathrm{fusion}}}{P_{\mathrm{external}}}
\]

Undefined / reported as NaN when \(P_{\mathrm{external}}=0\).

## 8. Energy residual

\[
\Delta E_{\mathrm{error}} = E_{\mathrm{initial}} + E_{\mathrm{input}} + E_{\mathrm{fusion}} - E_{\mathrm{final}} - E_{\mathrm{output}} - E_{\mathrm{loss}}
\]

Relative residual \(\lvert\Delta E_{\mathrm{error}}\rvert / E_{\mathrm{scale}}\) above threshold → warning, untrusted flag; strict mode aborts.
