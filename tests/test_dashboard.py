"""Synthetic operations dashboard tests."""

from __future__ import annotations

import json

import pytest

from energy_flex_trust.dashboard import load_scenarios, render_scenario


def test_bundled_scenarios_cover_normal_review_and_block() -> None:
    scenarios = load_scenarios()
    assert list(scenarios) == [
        "Healthy coordination",
        "Capacity stress",
        "Meter evidence gap",
        "Audit tampering detected",
    ]
    assert {scenario["disposition"] for scenario in scenarios.values()} == {
        "normal",
        "review",
        "block",
    }


def test_healthy_scenario_renders_reconciled_kpis() -> None:
    status, kpis, capacity, controls, assets, events, signals = render_scenario(
        "Healthy coordination"
    )
    assert "NORMAL" in status
    assert "445 kW" in kpis
    assert "£90.3" in kpis
    assert "BAT-GB-LON-01" in capacity
    assert all(row[1] == "PASS" for row in controls)
    assert len(assets) == 4
    assert len(events) == 5
    assert "No signal" in signals


@pytest.mark.parametrize(
    ("name", "expected_status", "expected_control", "expected_signal"),
    [
        ("Capacity stress", "REVIEW", "WARN", "Delivery variance"),
        ("Meter evidence gap", "BLOCK", "FAIL", "Incomplete meter evidence"),
        (
            "Audit tampering detected",
            "BLOCK",
            "FAIL",
            "Audit-chain integrity failure",
        ),
    ],
)
def test_risk_scenarios_surface_review_evidence(
    name: str,
    expected_status: str,
    expected_control: str,
    expected_signal: str,
) -> None:
    status, _kpis, _capacity, controls, _assets, _events, signals = render_scenario(
        name
    )
    assert expected_status in status
    assert any(row[1] == expected_control for row in controls)
    assert expected_signal in signals


def test_loader_rejects_non_synthetic_data(tmp_path) -> None:
    path = tmp_path / "scenario.json"
    path.write_text(
        json.dumps({"synthetic_data": False, "scenarios": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="synthetic"):
        load_scenarios(path)


def test_loader_rejects_capacity_ordering_error(tmp_path) -> None:
    payload = {
        "synthetic_data": True,
        "scenarios": [
            {
                "name": "Invalid",
                "disposition": "normal",
                "assets": [
                    {
                        "asset_id": "ASSET-1",
                        "capacity_kw": 10,
                        "offered_kw": 11,
                        "reserved_kw": 5,
                        "dispatched_kw": 4,
                        "delivered_kwh": 3,
                    }
                ],
                "controls": [],
            }
        ],
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="capacity ordering"):
        load_scenarios(path)


def test_loader_rejects_zero_capacity(tmp_path) -> None:
    payload = {
        "synthetic_data": True,
        "scenarios": [
            {
                "name": "Zero capacity",
                "disposition": "normal",
                "assets": [
                    {
                        "asset_id": "ASSET-0",
                        "capacity_kw": 0,
                        "offered_kw": 0,
                        "reserved_kw": 0,
                        "dispatched_kw": 0,
                        "delivered_kwh": 0,
                    }
                ],
                "controls": [],
            }
        ],
    }
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="positive capacity"):
        load_scenarios(path)


def test_unknown_scenario_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown dashboard scenario"):
        render_scenario("Production grid")
