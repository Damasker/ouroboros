#!/usr/bin/env python3
"""Build a static public site for GitHub Pages / ouroboros.beart.cc."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from ouroboros.core import run_simulation
from ouroboros.geometry import default_loop_geometry
from ouroboros.io import load_config, write_run_directory
from ouroboros.io.client_bridge import protocol_manifest

DEMO_SCENARIOS = (
    "passive",
    "oned-hlld",
    "magnetic-nozzle",
    "orbit-3dof",
    "dt-blanket-zones",
)


def _read_jsonl(path: Path) -> list[dict]:
    frames: list[dict] = []
    if not path.exists():
        return frames
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                frames.append(json.loads(line))
    return frames


def export_run_static(run_dir: Path, out_run: Path) -> dict:
    out_run.mkdir(parents=True, exist_ok=True)
    frames = _read_jsonl(run_dir / "snapshots.jsonl")
    (out_run / "snapshots.json").write_text(
        json.dumps({"run_id": run_dir.name, "offset": 0, "frames": frames}, indent=2) + "\n",
        encoding="utf-8",
    )
    if frames:
        (out_run / "latest.json").write_text(
            json.dumps(frames[-1], indent=2) + "\n", encoding="utf-8"
        )
    energy = run_dir / "energy_report.json"
    entry: dict = {"run_id": run_dir.name, "n_snapshots": len(frames)}
    if energy.exists():
        er = json.loads(energy.read_text(encoding="utf-8"))
        (out_run / "energy.json").write_text(
            json.dumps(er, indent=2) + "\n", encoding="utf-8"
        )
        entry["energy_trusted"] = er.get("energy_trusted")
        entry["relative_residual"] = (er.get("ledger") or {}).get("relative_residual")
    meta: dict = {"run_id": run_dir.name}
    for name in ("energy_report.json", "result.json", "events.json"):
        fp = run_dir / name
        if fp.exists():
            meta[name.replace(".json", "")] = json.loads(fp.read_text(encoding="utf-8"))
    (out_run / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    stream = run_dir / "client_stream.jsonl"
    if stream.exists():
        (out_run / "client-stream.json").write_text(
            json.dumps(
                {
                    "run_id": run_dir.name,
                    "protocol": "ouroboros.client",
                    "frames": _read_jsonl(stream),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return entry


def build_site(
    root: Path,
    *,
    out: Path,
    domain: str,
    scenarios: tuple[str, ...] = DEMO_SCENARIOS,
    skip_run: bool = False,
) -> Path:
    root = root.resolve()
    out = out.resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    geom_path = root / "geometry" / "loop_geometry.json"
    if not geom_path.exists():
        default_loop_geometry().save(str(geom_path))

    results = root / "results" / "_public_demo"
    if not skip_run:
        if results.exists():
            shutil.rmtree(results)
        results.mkdir(parents=True)
        from ouroboros.cli import SCENARIO_CONFIGS

        for sc in scenarios:
            cfg = load_config(root / SCENARIO_CONFIGS[sc])
            cfg.simulation.duration_s = min(float(cfg.simulation.duration_s), 0.12)
            cfg.simulation.output_interval_s = min(
                float(cfg.simulation.output_interval_s), 0.02
            )
            if cfg.simulation.model == "oned" and cfg.oned.cells_per_segment > 2:
                cfg.oned.cells_per_segment = 2
            result = run_simulation(cfg, run_id=sc)
            write_run_directory(result, results)
    elif not results.exists():
        raise SystemExit("No results/_public_demo — run without --skip-run first")

    data = out / "data"
    data.mkdir()
    runs_out = data / "runs"
    runs_out.mkdir()
    catalog: list[dict] = []
    for run_dir in sorted(results.iterdir()):
        if run_dir.is_dir():
            catalog.append(export_run_static(run_dir, runs_out / run_dir.name))

    (data / "runs.json").write_text(
        json.dumps({"runs": catalog}, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copyfile(geom_path, data / "geometry.json")
    (data / "health.json").write_text(
        json.dumps(
            {"status": "ok", "mode": "static", "domain": domain, "n_runs": len(catalog)},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (data / "client").mkdir()
    (data / "client" / "protocol.json").write_text(
        json.dumps(protocol_manifest(), indent=2) + "\n", encoding="utf-8"
    )

    viewer_dst = out / "viewer"
    shutil.copytree(root / "viewer", viewer_dst)
    # Resolve /data relative to site root whether on custom domain or /repo/ project Pages
    (viewer_dst / "config.js").write_text(
        """(function () {
  var path = location.pathname || '/';
  var root = path.indexOf('/viewer') >= 0 ? path.split('/viewer')[0] : '';
  if (root === '/') root = '';
  window.OUROBOROS = {
    mode: 'static',
    dataBase: root + '/data',
    domain: %s,
    siteRoot: root || '/'
  };
})();
"""
        % json.dumps(domain),
        encoding="utf-8",
    )

    (out / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Ouroboros</title>
  <script>
    var base = location.pathname.replace(/\\/index\\.html$/, '').replace(/\\/$/, '');
    location.replace(base + '/viewer/');
  </script>
</head>
<body>
  <p><a href="viewer/">Open Ouroboros viewer</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )
    # Write CNAME only when explicitly requested (needs DNS first, else github.io redirects to a dead host)
    write_cname = os.environ.get("WRITE_CNAME", "0") == "1"
    if write_cname and domain:
        (out / "CNAME").write_text(domain.strip() + "\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "404.html").write_text(
        (out / "index.html").read_text(encoding="utf-8"), encoding="utf-8"
    )

    print(f"Wrote static site → {out} ({len(catalog)} runs) domain={domain}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", default=".")
    p.add_argument("--out", default="site")
    p.add_argument("--domain", default="ouroboros.beart.cc")
    p.add_argument("--skip-run", action="store_true")
    args = p.parse_args()
    build_site(
        Path(args.root), out=Path(args.out), domain=args.domain, skip_run=args.skip_run
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
