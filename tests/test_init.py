"""Smoke tests for the DSpico integration package."""
import json
from pathlib import Path


def test_manifest_is_valid_json():
    manifest_path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "dspico"
        / "manifest.json"
    )
    data = json.loads(manifest_path.read_text())
    assert data["domain"] == "dspico"
    assert data["config_flow"] is True
    assert "webhook" in data["dependencies"]
    assert data["iot_class"] == "local_push"
