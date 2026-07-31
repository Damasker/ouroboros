"""Visualization layer — reads SimulationResult / CSV only; no physics."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _load_timeseries(run_dir: Path) -> dict[str, list[float]]:
    path = run_dir / "timeseries.csv"
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols: dict[str, list[float]] = {}
        for row in reader:
            for k, v in row.items():
                cols.setdefault(k, []).append(
                    float(v) if v not in ("", "nan", "NaN") else float("nan")
                )
    return cols


def _save(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)


def plot_all(run_dir: str | Path) -> list[Path]:
    run_dir = Path(run_dir)
    data = _load_timeseries(run_dir)
    t = np.asarray(data["time_s"])
    out_dir = run_dir / "plots"
    written: list[Path] = []

    def line(keys: list[str], title: str, ylabel: str, filename: str) -> None:
        fig, ax = plt.subplots(figsize=(8, 4))
        for k in keys:
            if k in data:
                ax.plot(t, data[k], label=k)
        ax.set_xlabel("t [s]")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)
        path = out_dir / filename
        _save(fig, path)
        written.append(path)

    line(["density_a", "density_b"], "Density A/B", "n [m^-3]", "density.png")
    line(["temp_a_ev", "temp_b_ev", "temp_chamber_ev"], "Temperatures", "T [eV]", "temperature.png")
    line(["mass_flow_a", "mass_flow_b"], "Mass flow", "ṁ [kg/s]", "mass_flow.png")
    line(
        ["current_throttle_a", "current_throttle_b"],
        "Throttle currents",
        "I [A]",
        "throttle_current.png",
    )
    line(["magnetic_energy"], "Magnetic energy", "E [J]", "magnetic_energy.png")
    line(
        ["fusion_power_w", "alpha_power_w", "neutron_power_w"],
        "Fusion powers",
        "P [W]",
        "fusion_power.png",
    )
    line(
        ["external_power_w", "controller_heater_w"], "External power", "P [W]", "external_power.png"
    )
    line(["loss_power_w", "recovered_power_w"], "Losses / recovery", "P [W]", "losses.png")
    line(
        ["internal_energy_total_j", "kinetic_energy_j", "magnetic_energy", "wall_energy_j"],
        "Energy inventory",
        "E [J]",
        "energy_balance.png",
    )
    line(
        ["energy_residual_j", "energy_residual_rel"],
        "Energy residual",
        "J / -",
        "energy_residual.png",
    )

    # Phase portraits
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(data["density_a"], data["density_b"], lw=1.0)
    ax.set_xlabel("density A")
    ax.set_ylabel("density B")
    ax.set_title("Phase: density A vs B")
    ax.grid(True, alpha=0.3)
    p = out_dir / "phase_density_ab.png"
    _save(fig, p)
    written.append(p)

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(data["mass_flow_a"], data["current_throttle_a"], lw=1.0)
    ax.set_xlabel("mass flow A")
    ax.set_ylabel("throttle current A")
    ax.set_title("Phase: flow vs throttle current")
    ax.grid(True, alpha=0.3)
    p = out_dir / "phase_flow_current.png"
    _save(fig, p)
    written.append(p)

    # Simple schematic snapshot (final frame)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_xlim(-3, 4)
    ax.set_ylim(-3, 2)
    ax.set_aspect("equal")
    ax.set_title("Loop schematic (final state)")
    # Draw segments
    dens_a = data["density_a"][-1]
    dens_b = data["density_b"][-1]
    scale = max(dens_a, dens_b, 1.0)
    ax.annotate(
        "",
        xy=(-0.5, 1.0),
        xytext=(-2.0, 1.0),
        arrowprops={"arrowstyle": "->", "color": "C0", "lw": 1 + 3 * dens_a / scale},
    )
    ax.annotate(
        "",
        xy=(-0.5, -1.0),
        xytext=(-2.0, -1.0),
        arrowprops={"arrowstyle": "->", "color": "C1", "lw": 1 + 3 * dens_b / scale},
    )
    chamber = plt.Circle(
        (0.5, 0.0),
        0.4,
        color="crimson",
        alpha=min(0.2 + data["fusion_power_w"][-1] / (1e6 + 1), 0.9),
    )
    ax.add_patch(chamber)
    ax.text(-2.0, 1.2, f"A n={dens_a:.2e}", fontsize=8)
    ax.text(-2.0, -1.3, f"B n={dens_b:.2e}", fontsize=8)
    ax.text(0.1, 0.0, "Chamber", fontsize=8, color="white")
    ax.text(1.5, 0.3, "Expand→Sep→Return", fontsize=8)
    ax.plot([1.0, 3.0, 2.0, -2.0, -2.0], [0.0, 0.0, -2.0, -2.0, 1.0], "k--", alpha=0.5)
    ax.axis("off")
    p = out_dir / "schematic.png"
    _save(fig, p)
    written.append(p)

    # Multi-zone spatial profile (final frame), if present
    zone_keys = sorted(k for k in data if k.startswith("zone_density:"))
    if zone_keys:
        ids = [k.split(":", 1)[1] for k in zone_keys]
        dens = [data[k][-1] for k in zone_keys]
        temps = [data.get(f"zone_temp_ev:{zid}", [float("nan")])[-1] for zid in ids]
        fig, ax = plt.subplots(figsize=(10, 4))
        x = np.arange(len(ids))
        ax.bar(x - 0.15, dens, width=0.3, label="density")
        ax2 = ax.twinx()
        ax2.plot(x, temps, color="C1", marker="o", label="T [eV]")
        ax.set_xticks(x)
        ax.set_xticklabels(ids, rotation=45, ha="right", fontsize=7)
        ax.set_ylabel("n [m^-3]")
        ax2.set_ylabel("T [eV]")
        ax.set_title("Multi-zone profile (final)")
        ax.grid(True, alpha=0.3)
        p = out_dir / "zone_profile.png"
        _save(fig, p)
        written.append(p)

    # 1D cell density along branch_a if present
    cell_a = sorted(
        (k for k in data if k.startswith("cell_density:branch_a:")),
        key=lambda s: int(s.rsplit(":", 1)[1]),
    )
    if cell_a:
        fig, ax = plt.subplots(figsize=(8, 4))
        for k in cell_a:
            ax.plot(t, data[k], label=k.split(":")[-1])
        ax.set_xlabel("t [s]")
        ax.set_ylabel("n [m^-3]")
        ax.set_title("1D cells: branch_a density")
        ax.legend(title="cell")
        ax.grid(True, alpha=0.3)
        p = out_dir / "oned_branch_a_cells.png"
        _save(fig, p)
        written.append(p)

    manifest = {"plots": [str(x.name) for x in written]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return written
