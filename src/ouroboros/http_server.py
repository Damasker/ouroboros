"""Read-only HTTP snapshot server for 3D clients (stdlib only)."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def _list_runs(results_root: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if not results_root.exists():
        return runs
    for p in sorted(results_root.iterdir()):
        if not p.is_dir():
            continue
        snap = p / "snapshots.jsonl"
        energy = p / "energy_report.json"
        if not snap.exists() and not energy.exists():
            # Campaign dirs nest runs; skip non-run folders without artifacts
            continue
        entry: dict[str, Any] = {"run_id": p.name, "path": str(p)}
        if energy.exists():
            try:
                er = json.loads(energy.read_text(encoding="utf-8"))
                entry["energy_trusted"] = er.get("energy_trusted")
                entry["relative_residual"] = (er.get("ledger") or {}).get("relative_residual")
            except (json.JSONDecodeError, OSError):
                pass
        if snap.exists():
            entry["n_snapshots"] = sum(1 for _ in snap.open(encoding="utf-8"))
        runs.append(entry)
    return runs


def _read_jsonl(path: Path, *, offset: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < offset:
                continue
            line = line.strip()
            if not line:
                continue
            frames.append(json.loads(line))
            if limit is not None and len(frames) >= limit:
                break
    return frames


def _latest_frame(path: Path) -> dict[str, Any] | None:
    last: dict[str, Any] | None = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                last = json.loads(line)
    return last


def make_handler(results_root: Path) -> type[BaseHTTPRequestHandler]:
    root = results_root.resolve()

    class SnapshotHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            logger.info("%s - %s", self.address_string(), fmt % args)

        def _send(self, code: int, payload: Any, content_type: str = "application/json") -> None:
            body = (
                payload
                if isinstance(payload, (bytes, bytearray))
                else (json.dumps(payload, indent=2) + "\n").encode("utf-8")
            )
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _not_found(self, msg: str = "not found") -> None:
            self._send(404, {"error": msg})

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            if path in ("/", "/health"):
                self._send(200, {"status": "ok", "results_root": str(root)})
                return

            if path == "/runs":
                self._send(200, {"runs": _list_runs(root)})
                return

            parts = path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "runs":
                run_id = parts[1]
                run_dir = (root / run_id).resolve()
                if not str(run_dir).startswith(str(root)) or not run_dir.is_dir():
                    self._not_found(f"run {run_id}")
                    return

                if len(parts) == 2:
                    meta: dict[str, Any] = {"run_id": run_id}
                    for name in ("energy_report.json", "result.json", "events.json"):
                        fp = run_dir / name
                        if fp.exists():
                            meta[name.replace(".json", "")] = json.loads(
                                fp.read_text(encoding="utf-8")
                            )
                    self._send(200, meta)
                    return

                resource = parts[2]
                if resource == "energy":
                    fp = run_dir / "energy_report.json"
                    if not fp.exists():
                        self._not_found("energy_report.json")
                        return
                    self._send(200, json.loads(fp.read_text(encoding="utf-8")))
                    return

                if resource == "snapshots":
                    fp = run_dir / "snapshots.jsonl"
                    if not fp.exists():
                        self._not_found("snapshots.jsonl")
                        return
                    if len(parts) >= 4 and parts[3] == "latest":
                        frame = _latest_frame(fp)
                        if frame is None:
                            self._not_found("empty snapshots")
                            return
                        self._send(200, frame)
                        return
                    offset = int(qs.get("offset", ["0"])[0])
                    limit_raw = qs.get("limit", [None])[0]
                    limit = int(limit_raw) if limit_raw is not None else None
                    frames = _read_jsonl(fp, offset=offset, limit=limit)
                    self._send(200, {"run_id": run_id, "offset": offset, "frames": frames})
                    return

                if resource == "timeseries":
                    fp = run_dir / "timeseries.csv"
                    if not fp.exists():
                        self._not_found("timeseries.csv")
                        return
                    self._send(200, fp.read_bytes(), content_type="text/csv; charset=utf-8")
                    return

            self._not_found(path)

    return SnapshotHandler


def serve_snapshots(
    results_root: str | Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    """Create and return a bound HTTP server (caller runs serve_forever)."""
    root = Path(results_root)
    root.mkdir(parents=True, exist_ok=True)
    handler = make_handler(root)
    httpd = ThreadingHTTPServer((host, port), handler)
    logger.info("Snapshot server listening on http://%s:%d (root=%s)", host, port, root)
    return httpd


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Ouroboros snapshot HTTP server")
    p.add_argument("--root", default=".", help="Project root")
    p.add_argument("--results", default="results", help="Results directory (relative to root)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = Path(args.root) / args.results
    httpd = serve_snapshots(results, host=args.host, port=args.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
