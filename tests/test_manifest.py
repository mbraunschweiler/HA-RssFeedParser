"""Tests for integration manifest requirements."""

import json
from pathlib import Path


def test_feedparser_requirement_allows_home_assistant_updates() -> None:
    manifest_path = (
        Path(__file__).parents[1] / "custom_components" / "rss_parser" / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["requirements"] == ["feedparser>=6.0.12"]
