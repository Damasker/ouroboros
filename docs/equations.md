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

### 2b. Dynamic blanket (Milestone 9)

\[
\frac{dE_b}{dt} = f_{\mathrm{capture}} P_n - \frac{E_b}{\tau_{\mathrm{cool}}},\qquad
P_{\mathrm{leak}}=(1-f_{\mathrm{capture}})P_n
\]

Classification: phenomenological / simplified. Optional TBR stub scales breeding rate with captured neutron reaction rate proxy. When `blanket.enabled=false`, \(P_n\) is an instant ledger output (legacy).

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

## 4b. Consistent electromechanical coupling (Milestone 8)

\[
F_{\mathrm{mag}}=-k_{\mathrm{em}} I,\qquad
L\frac{dI}{dt}+R I=k_{\mathrm{em}} v
\]

Units: \(k_{\mathrm{em}}\) in N/A = V/(m/s). Then \(\frac{d}{dt}(E_{\mathrm{kin}}+E_{\mathrm{mag}})=F_{\mathrm{other}}v-I^2R\). Classification: simplified / phenomenological electromechanics. Config: `coupling_mode: consistent`.

Legacy `phenomenological` mode (independent force coeff + \(M dI_p/dt\)) remains available but may leave a ledger residual.

## 4c. Reduced-MHD-like forces (Milestone 10)

Split path forces (classification: phenomenological / simplified):

1. **Alfvén-like drag** \(F_{\mathrm{d}}=-f\rho v_A v\) → dissipative; power \(\max(-F_{\mathrm{d}}v,0)\) enters the friction ledger channel.
2. **Magnetic-pressure stiffness** \(F_{\mathrm{mp}}=-\mathrm{scale}\,(B^2/2\mu_0)\,A\,\tanh(v/v_0)\) with \(B\sim\mu_0 n I\).
3. **Hydrodynamic \(\Delta p\,A\)** \(F_p=\kappa(p_{\mathrm{up}}-p_{\mathrm{down}})A\).

When `compressional_exchange: true`, channels (2)–(3) exchange with plasma internal energy:

\[
P_{\mathrm{heat}}=-(F_{\mathrm{mp}}+F_p)\cdot v
\quad\Rightarrow\quad
\frac{d}{dt}(E_{\mathrm{kin}}+E_{\mathrm{int}})=0
\]

from these forces alone (Alfvén drag still leaves via the ledger). Disable exchange only for legacy comparisons — residual may grow.

## 4d. 1D cell-pressure path forces (Milestone 11)

For `oned.momentum_mode: cell_pressure`, each mesh face contributes

\[
F_{\mathrm{face}}=\kappa(p_L-p_R)A
\]

summed onto path A/B (common faces split ½). Face work \(F_{\mathrm{face}} u_{\mathrm{path}}\) is removed equally from the two adjacent cell internal energies. Classification: simplified hydro mapped onto dual-path ODEs — **not** a cell-local velocity field.

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
