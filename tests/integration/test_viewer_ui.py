"""Viewer UI chrome / design assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_shared_styles_exist():
    css = (ROOT / "viewer" / "styles.css").read_text(encoding="utf-8")
    assert "--phosphor" in css
    assert ".brand" in css
    assert "@keyframes" in css


def test_schematic_app_shell():
    html = (ROOT / "viewer" / "index.html").read_text(encoding="utf-8")
    assert "Ouroboros" in html
    assert "snapshot viewer" in html.lower()
    assert "styles.css" in html
    assert "webgpu.html" in html
    assert "protocol.html" in html
    assert 'id="play"' in html
    assert "Space" in html


def test_protocol_page():
    html = (ROOT / "viewer" / "protocol.html").read_text(encoding="utf-8")
    assert "Ouroboros" in html
    assert "/client/protocol" in html
