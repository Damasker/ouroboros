"""Parametric campaign runner (Milestone 9)."""

from __future__ import annotations

import csv
import itertools
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ouroboros.core import run_simulation
from ouroboros.domain.config import SimulationConfig
from ouroboros.io import load_config, write_run_directory

logger = logging.getLogger(__name__)


@dataclass
class SweepParam:
    path: str
    values: list[Any]


@dataclass
class CampaignSpec:
    name: str
    base_config: Path
    output_dir: Path
    parameters: list[SweepParam] = field(default_factory=list)
    overrides: dict[str, Any] = field(default_factory=dict)


def _set_dotted(cfg: SimulationConfig, path: str, value: Any) -> SimulationConfig:
    data = cfg.model_dump()
    parts = path.split(".")
    cur: Any = data
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            raise KeyError(f"Invalid override path: {path}")
        cur = cur[p]
    cur[parts[-1]] = value
    return SimulationConfig.model_validate(data)


def load_campaign(path: str | Path, *, root: Path) -> CampaignSpec:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    params = [
        SweepParam(path=p["path"], values=list(p["values"])) for p in raw.get("parameters", [])
    ]
    base = Path(raw["base_config"])
    if not base.is_absolute():
        base = (root / base).resolve()
    out = Path(raw.get("output_dir", f"results/campaigns/{raw['name']}"))
    if not out.is_absolute():
        out = root / out
    return CampaignSpec(
        name=str(raw["name"]),
        base_config=base,
        output_dir=out,
        parameters=params,
        overrides=dict(raw.get("overrides") or {}),
    )


def expand_cases(spec: CampaignSpec) -> list[dict[str, Any]]:
    if not spec.parameters:
        return [{}]
    keys = [p.path for p in spec.parameters]
    value_lists = [p.values for p in spec.parameters]
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*value_lists)]


def _run_slug(case: dict[str, Any]) -> str:
    parts: list[str] = []
    for k, v in case.items():
        key = k.split(".")[-1]
        if isinstance(v, float):
            parts.append(f"{key}_{v:.3g}")
        else:
            parts.append(f"{key}_{v}")
    slug = "_".join(parts).replace(" ", "").replace("+", "")
    return slug[:72] if slug else "base"


def run_campaign(
    spec: CampaignSpec,
    *,
    write_artifacts: bool = True,
) -> dict[str, Any]:
    """Run cartesian product of parameter sweeps; optionally write runs + summary."""
    base = load_config(spec.base_config)
    for path, value in spec.overrides.items():
        base = _set_dotted(base, path, value)

    out_dir = spec.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    cases = expand_cases(spec)
    rows: list[dict[str, Any]] = []
    for i, case in enumerate(cases):
        cfg = base
        for path, value in case.items():
            cfg = _set_dotted(cfg, path, value)
        run_id = f"{spec.name}_{i:03d}_{_run_slug(case)}"
        logger.info("Campaign %s case %d/%d run_id=%s", spec.name, i + 1, len(cases), run_id)
        result = run_simulation(cfg, run_id=run_id)
        if write_artifacts:
            write_run_directory(result, out_dir)
        fus = result.series.get("fusion_power_w", [0.0])
        q = result.series.get("q_factor", [float("nan")])
        q_ok = [x for x in q if isinstance(x, (int, float)) and x == x]
        row: dict[str, Any] = {
            "run_id": run_id,
            "energy_trusted": result.energy_trusted,
            "relative_residual": result.ledger_final.relative_residual,
            "e_error_j": result.ledger_final.e_error_j,
            "fusion_power_max_w": max(fus) if fus else 0.0,
            "q_max": max(q_ok) if q_ok else float("nan"),
            "n_samples": len(result.times_s),
            "blanket_dynamic": result.ledger_final.blanket_dynamic,
            "e_coolant_extracted_j": result.ledger_final.e_coolant_extracted_j,
            "e_neutron_leaked_j": result.ledger_final.e_neutron_leaked_j,
            "e_blanket_j": result.ledger_final.e_blanket_j,
        }
        for path, value in case.items():
            row[f"param:{path}"] = value
        rows.append(row)

    summary: dict[str, Any] = {
        "campaign": spec.name,
        "n_cases": len(rows),
        "base_config": str(spec.base_config),
        "cases": rows,
    }
    if write_artifacts:
        (out_dir / "campaign_summary.json").write_text(
            json.dumps(summary, indent=2) + "\n", encoding="utf-8"
        )
        if rows:
            fieldnames = list(rows[0].keys())
            with (out_dir / "campaign_summary.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        logger.info("Campaign summary written to %s", out_dir)
    return summary
