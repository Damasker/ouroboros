"""Milestone 21: WebGPU volumetric viewer assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_webgpu_viewer_exists():
    path = ROOT / "viewer" / "webgpu.html"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "navigator.gpu" in text
    assert "/runs" in text
    assert "Ouroboros" in text


def test_canvas_viewer_links_webgpu():
    index = (ROOT / "viewer" / "index.html").read_text(encoding="utf-8")
    assert "webgpu.html" in index
