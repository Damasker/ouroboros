"""Command-line entrypoint."""

from __future__ import annotations

import argparse
import logging
import math
import sys
from pathlib import Path

from ouroboros.core import run_simulation
from ouroboros.geometry import default_loop_geometry
from ouroboros.io import load_config, write_run_directory
from ouroboros.viz import plot_all

SCENARIO_CONFIGS = {
    "passive": "configs/passive.yaml",
    "driven": "configs/driven.yaml",
    "synthetic-oscillation": "configs/synthetic_oscillation.yaml",
    "dt-fusion": "configs/dt_fusion.yaml",
    "dt-blanket": "configs/dt_blanket.yaml",
    "coupled-throttle": "configs/coupled_throttle.yaml",
    "multizone-passive": "configs/multizone_passive.yaml",
    "multizone-driven": "configs/multizone_driven.yaml",
    "oned-passive": "configs/oned_passive.yaml",
    "oned-driven": "configs/oned_driven.yaml",
    "coupled-consistent": "configs/coupled_consistent.yaml",
    "multizone-dt": "configs/multizone_dt.yaml",
    "oned-dt": "configs/oned_dt.yaml",
    "oned-cell-momentum": "configs/oned_cell_momentum.yaml",
    "oned-cell-velocity": "configs/oned_cell_velocity.yaml",
    "oned-momentum-flux": "configs/oned_momentum_flux.yaml",
    "oned-rusanov": "configs/oned_rusanov.yaml",
    "oned-hllc": "configs/oned_hllc.yaml",
    "oned-energy-flux": "configs/oned_energy_flux.yaml",
    "oned-hllc-energy": "configs/oned_hllc_energy.yaml",
    "magnetic-nozzle": "configs/magnetic_nozzle.yaml",
    "reduced-mhd": "configs/reduced_mhd.yaml",
    "fault-block-a": "configs/faults/block_branch_a.yaml",
    "fault-quench": "configs/faults/quench.yaml",
    "fault-heater-trip": "configs/faults/heater_trip.yaml",
    "fault-helium": "configs/faults/helium_ash.yaml",
    "fault-density-spike": "configs/faults/density_spike.yaml",
    "fault-cooling-loss": "configs/faults/cooling_loss.yaml",
}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_run(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.scenario:
        cfg_path = root / SCENARIO_CONFIGS[args.scenario]
    else:
        cfg_path = Path(args.config)
    config = load_config(cfg_path)
    # Ensure geometry asset exists
    geom_path = root / "geometry" / "loop_geometry.json"
    if not geom_path.exists():
        default_loop_geometry().save(geom_path)
    result = run_simulation(config, run_id=args.run_id)
    out = write_run_directory(result, root / "results")
    print(f"run_id={result.run_id}")
    print(f"output={out}")
    print(f"energy_trusted={result.energy_trusted}")
    print(f"relative_residual={result.ledger_final.relative_residual:.6e}")
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    root = Path(args.root)
    run_dir = root / "results" / args.run
    if not run_dir.exists():
        print(f"Run directory not found: {run_dir}", file=sys.stderr)
        return 1
    paths = plot_all(run_dir)
    print(f"wrote {len(paths)} plots to {run_dir / 'plots'}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Write a short stability / energy summary for a run."""
    import json

    run_dir = Path(args.root) / "results" / args.run
    energy = json.loads((run_dir / "energy_report.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    series = result["series"]
    report_lines = [
        f"# Stability report for {args.run}",
        "",
        f"- energy_trusted: {energy['energy_trusted']}",
        f"- relative_residual: {energy['ledger']['relative_residual']:.6e}",
        f"- e_error_j: {energy['ledger']['e_error_j']:.6e}",
        f"- scenario: {result['metadata'].get('scenario')}",
        f"- n_samples: {len(result['times_s'])}",
    ]
    ledger = energy.get("ledger", {})
    if ledger.get("blanket_dynamic"):
        report_lines.append(f"- blanket_energy_j: {ledger.get('e_blanket_j', 0):.4g}")
        report_lines.append(f"- coolant_extracted_j: {ledger.get('e_coolant_extracted_j', 0):.4g}")
        report_lines.append(f"- neutron_leaked_j: {ledger.get('e_neutron_leaked_j', 0):.4g}")
    if series.get("q_factor"):
        qs = [q for q in series["q_factor"] if not (isinstance(q, float) and math.isnan(q))]
        if qs:
            report_lines.append(f"- Q max: {max(qs):.4g}")
            report_lines.append(f"- Q final: {qs[-1]:.4g}")
    fa = series.get("flow_a", [0])
    fb = series.get("flow_b", [0])
    report_lines.append(f"- flow_a final: {fa[-1]:.4g} m/s")
    report_lines.append(f"- flow_b final: {fb[-1]:.4g} m/s")
    out = run_dir / "stability_report.md"
    out.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


def cmd_campaign(args: argparse.Namespace) -> int:
    from ouroboros.campaign import load_campaign, run_campaign

    root = Path(args.root)
    camp_path = Path(args.campaign)
    if not camp_path.is_absolute():
        camp_path = root / camp_path
    spec = load_campaign(camp_path, root=root)
    if args.output:
        out = Path(args.output)
        spec.output_dir = out if out.is_absolute() else root / out
    summary = run_campaign(spec, write_artifacts=True)
    print(f"campaign={summary['campaign']}")
    print(f"n_cases={summary['n_cases']}")
    print(f"output={spec.output_dir}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from ouroboros.http_server import serve_snapshots

    root = Path(args.root)
    results = Path(args.results)
    if not results.is_absolute():
        results = root / results
    httpd = serve_snapshots(
        results, host=args.host, port=args.port, project_root=root
    )
    print(f"serving {results} on http://{args.host}:{args.port}/")
    print(f"viewer  http://{args.host}:{args.port}/viewer")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("shutdown")
    finally:
        httpd.server_close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ouroboros", description="Ouroboros Plasma Loop Simulator")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run a scenario or config")
    run_p.add_argument("--scenario", choices=sorted(SCENARIO_CONFIGS.keys()))
    run_p.add_argument("--config", help="Path to YAML config")
    run_p.add_argument("--run-id", default=None)
    run_p.set_defaults(func=cmd_run)

    viz_p = sub.add_parser("visualize", help="Plot a completed run")
    viz_p.add_argument("--run", required=True, help="Run id under results/")
    viz_p.set_defaults(func=cmd_visualize)

    rep_p = sub.add_parser("report", help="Write stability report")
    rep_p.add_argument("--run", required=True)
    rep_p.set_defaults(func=cmd_report)

    camp_p = sub.add_parser("campaign", help="Run a parametric campaign YAML")
    camp_p.add_argument("--campaign", required=True, help="Path to campaign YAML")
    camp_p.add_argument("--output", default=None, help="Override output directory")
    camp_p.set_defaults(func=cmd_campaign)

    srv_p = sub.add_parser("serve", help="HTTP snapshot server for 3D clients")
    srv_p.add_argument("--results", default="results")
    srv_p.add_argument("--host", default="127.0.0.1")
    srv_p.add_argument("--port", type=int, default=8765)
    srv_p.set_defaults(func=cmd_serve)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    if args.command == "run" and not args.scenario and not args.config:
        parser.error("Provide --scenario or --config")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
