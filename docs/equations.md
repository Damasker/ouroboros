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

## 4e. Cell-local axial velocity (Milestone 12)

With `oned.momentum_mode: cell_velocity`, each cell carries \(V_i\). Pressure forces use face pressures \(p_f=\tfrac12(p_L+p_R)\):

\[
F_i=\kappa A(p_{i-1/2}-p_{i+1/2}),\qquad
m_i=\frac{V_i}{V_{\mathrm{tot}}}M_{\mathrm{eff}},\qquad
m_i\dot V_i=F_i+F_{\mathrm{fric},i}+F_{\mathrm{drive},i}+F_{\mathrm{mag},i}.
\]

Compressional exchange: \(\dot U_i=-F_i^{\mathrm{pressure}} V_i\). Throttle circuits couple to mass-weighted path means. Classification: simplified 1D FV momentum — not a Riemann MHD solver.

## 4f. Magnetic nozzle (Milestone 13)

From zone inventory \(N,U\) (expansion zone, or chamber in lumped):

\[
\dot N_{\mathrm{ex}}=f\frac{N}{\tau},\qquad
P_{\mathrm{th}}=\frac{U}{N}\dot N_{\mathrm{ex}},\qquad
P_{\mathrm{jet}}=\eta P_{\mathrm{th}},\qquad
P_{\mathrm{waste}}=(1-\eta)P_{\mathrm{th}}.
\]

Then \(\dot m=m_p\dot N_{\mathrm{ex}}\), \(v_{\mathrm{ex}}=\sqrt{2P_{\mathrm{jet}}/\dot m}\), \(T=\dot m\,v_{\mathrm{ex}}\), \(I_{\mathrm{sp}}=v_{\mathrm{ex}}/g_0\).
Ledger: \(E_{\mathrm{thrust}}=\int P_{\mathrm{jet}}\) (output), waste adds to exhaust. Classification: **phenomenological / speculative**.

## 4g. Upwind momentum flux (Milestone 14)

For `cell_velocity` with `oned.momentum_flux: true`:

\[
\Phi = u_{\mathrm{eff}} A \rho_{\mathrm{up}} v_{\mathrm{up}},\qquad
\rho_{\mathrm{up}}=m_{\mathrm{up}}/V_{\mathrm{up}},\qquad
m_i\dot v_i += -(\Phi_{\mathrm{out}}-\Phi_{\mathrm{in}}).
\]

Upwinding typically yields \(\sum m_i v_i\dot v_i^{\mathrm{flux}}\le 0\); with `thermalize_momentum_flux` that sink is deposited into cell internal energy (numerical viscosity). Classification: simplified FV — not a Riemann MHD solver.

## 4h. Rusanov flux (Milestone 15)

With `oned.riemann: rusanov` (\(F=\rho v^2+\kappa p\)):

\[
\frac{\Phi}{A}=\tfrac12(F_L+F_R)-\tfrac12 S(\rho v_R-\rho v_L),\qquad
S=\max(|v_L|+c_L,|v_R|+c_R),\quad c\sim\sqrt{\kappa p/\rho}.
\]

Separate \(\nabla p\) / upwind momentum flux are disabled. Energy: \(\dot U_{\mathrm{tot}}=-\sum m_i v_i\dot v_i^{\mathrm{Rusanov}}\). Classification: simplified Local Lax–Friedrichs — not HLLC/Roe/MHD.

## 4i. HLLC flux (Milestone 16)

With `oned.riemann: hllc` (same \(F=\rho v^2+\kappa p\), \(c\sim\sqrt{\kappa p/\rho}\)):

\[
S_L=\min(v_L-c_L,v_R-c_R),\quad
S_R=\max(v_L+c_L,v_R+c_R),\quad
S_M=\frac{\rho_R v_R(S_R-v_R)-\rho_L v_L(S_L-v_L)+p_L-p_R}
{\rho_R(S_R-v_R)-\rho_L(S_L-v_L)}.
\]

Star momenta \(\rho^* S_M\) feed the usual HLLC piecewise flux; \(\nabla p\) / upwind are disabled. Energy: \(\dot U_{\mathrm{tot}}=-\sum m_i v_i\dot v_i^{\mathrm{HLLC}}\). Classification: simplified HLLC on phenomenological masses — not full Euler/MHD HLLC.

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
