"""Credential-free, read-only dashboard for synthetic operational scenarios."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).with_name("demo_data") / "operations_scenarios.json"
DISPOSITIONS = {"normal", "review", "block"}
CONTROL_STATUSES = {"pass", "warn", "fail"}


def load_scenarios(path: Path = DATA_PATH) -> dict[str, dict[str, Any]]:
    """Load and validate the bundled synthetic dashboard scenarios."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("synthetic_data") is not True:
        raise ValueError("Dashboard data must be explicitly marked as synthetic.")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Dashboard data must contain at least one scenario.")

    indexed: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        _validate_scenario(scenario)
        name = scenario["name"]
        if name in indexed:
            raise ValueError(f"Duplicate dashboard scenario: {name}")
        indexed[name] = scenario
    return indexed


def _validate_scenario(scenario: dict[str, Any]) -> None:
    name = scenario.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Every scenario requires a non-empty name.")
    if scenario.get("disposition") not in DISPOSITIONS:
        raise ValueError(f"Scenario {name} has an invalid disposition.")

    assets = scenario.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError(f"Scenario {name} requires at least one asset.")
    asset_ids: set[str] = set()
    for asset in assets:
        asset_id = asset.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id:
            raise ValueError(f"Scenario {name} has an asset without an ID.")
        if asset_id in asset_ids:
            raise ValueError(f"Scenario {name} repeats asset {asset_id}.")
        asset_ids.add(asset_id)
        values = [
            float(asset[field])
            for field in (
                "capacity_kw",
                "offered_kw",
                "reserved_kw",
                "dispatched_kw",
                "delivered_kwh",
            )
        ]
        if any(value < 0 for value in values):
            raise ValueError(f"Scenario {name} contains a negative asset value.")
        capacity, offered, reserved, dispatched, _delivered = values
        if capacity == 0:
            raise ValueError(
                f"Scenario {name} requires positive capacity for {asset_id}."
            )
        if not capacity >= offered >= reserved >= dispatched:
            raise ValueError(
                f"Scenario {name} violates capacity ordering for {asset_id}."
            )

    for control in scenario.get("controls", []):
        if control.get("status") not in CONTROL_STATUSES:
            raise ValueError(f"Scenario {name} has an invalid control status.")


def scenario_names() -> list[str]:
    return list(load_scenarios())


def _number(value: float) -> str:
    return f"{value:,.1f}".rstrip("0").rstrip(".")


def _kpi_card(label: str, value: str, detail: str, tone: str) -> str:
    safe = [html.escape(part) for part in (label, value, detail, tone)]
    return (
        f'<div class="eft-kpi {safe[3]}">'
        f'<span class="eft-kpi-label">{safe[0]}</span>'
        f'<strong>{safe[1]}</strong>'
        f'<small>{safe[2]}</small></div>'
    )


def _render_kpis(scenario: dict[str, Any]) -> str:
    assets = scenario["assets"]
    capacity = sum(float(asset["capacity_kw"]) for asset in assets)
    reserved = sum(float(asset["reserved_kw"]) for asset in assets)
    dispatched = sum(float(asset["dispatched_kw"]) for asset in assets)
    delivered = sum(float(asset["delivered_kwh"]) for asset in assets)
    settlement = scenario["settlement"]
    headroom = capacity - reserved
    ready = bool(settlement["ready"])
    evidence = float(settlement["evidence_coverage_percent"])
    signal_count = len(scenario.get("signals", []))
    cards = [
        _kpi_card("Fleet capacity", f"{_number(capacity)} kW", "registered", "blue"),
        _kpi_card(
            "Reserved",
            f"{_number(reserved)} kW",
            f"{_number(headroom)} kW headroom",
            "amber",
        ),
        _kpi_card(
            "Dispatched",
            f"{_number(dispatched)} kW",
            f"{_number(delivered)} kWh delivered",
            "green",
        ),
        _kpi_card("Evidence", f"{_number(evidence)}%", "interval coverage", "violet"),
        _kpi_card(
            "Settlement",
            f"£{_number(float(settlement['amount_gbp']))}",
            "ready" if ready else "held",
            "green" if ready else "red",
        ),
        _kpi_card(
            "Risk signals",
            str(signal_count),
            "requires review" if signal_count else "none detected",
            "red" if signal_count else "green",
        ),
    ]
    return '<div class="eft-kpi-grid">' + "".join(cards) + "</div>"


def _render_capacity(scenario: dict[str, Any]) -> str:
    rows: list[str] = []
    for asset in scenario["assets"]:
        capacity = float(asset["capacity_kw"])
        offered = float(asset["offered_kw"]) / capacity * 100
        reserved = float(asset["reserved_kw"]) / capacity * 100
        dispatched = float(asset["dispatched_kw"]) / capacity * 100
        asset_id = html.escape(asset["asset_id"])
        rows.append(
            '<div class="eft-capacity-row">'
            f'<div class="eft-capacity-label"><strong>{asset_id}</strong>'
            f'<span>{_number(capacity)} kW</span></div>'
            '<div class="eft-track">'
            f'<span class="offered" style="width:{offered:.2f}%"></span>'
            f'<span class="reserved" style="width:{reserved:.2f}%"></span>'
            f'<span class="dispatched" style="width:{dispatched:.2f}%"></span>'
            "</div></div>"
        )
    legend = (
        '<div class="eft-legend"><span class="l-offered">Offered</span>'
        '<span class="l-reserved">Reserved</span>'
        '<span class="l-dispatched">Dispatched</span></div>'
    )
    return '<div class="eft-capacity">' + "".join(rows) + legend + "</div>"


def _status_markdown(scenario: dict[str, Any]) -> str:
    labels = {
        "normal": ("✅ NORMAL", "Configured controls report no blocking signal."),
        "review": (
            "⚠️ REVIEW",
            "An authorized operator should review the evidence.",
        ),
        "block": ("🛑 BLOCK", "Evidence-dependent settlement remains stopped."),
    }
    title, guidance = labels[scenario["disposition"]]
    return (
        f"## {title}\n\n{scenario['description']}\n\n"
        f"**Snapshot:** `{scenario['as_of']}` · {guidance}"
    )


def _signals_markdown(scenario: dict[str, Any]) -> str:
    signals = scenario.get("signals", [])
    if not signals:
        return (
            "### Review signals\n\nNo signal is present in this synthetic snapshot. "
            "A clean view is not authorization to dispatch or settle."
        )
    lines = ["### Review signals"]
    for signal in signals:
        severity = str(signal["severity"]).upper()
        lines.append(
            f"- **{severity} — {signal['title']}:** {signal['action']}"
        )
    return "\n\n".join(lines)


def render_scenario(
    scenario_name: str,
) -> tuple[str, str, str, list[list[str]], list[list[str]], list[list[str]], str]:
    """Return presentation values for a selected synthetic scenario."""

    scenarios = load_scenarios()
    if scenario_name not in scenarios:
        raise ValueError(f"Unknown dashboard scenario: {scenario_name}")
    scenario = scenarios[scenario_name]
    controls = [
        [control["name"], control["status"].upper(), control["evidence"]]
        for control in scenario["controls"]
    ]
    assets = [
        [
            asset["asset_id"],
            asset["asset_type"],
            asset["location"],
            _number(float(asset["capacity_kw"])),
            _number(float(asset["reserved_kw"])),
            _number(float(asset["dispatched_kw"])),
            _number(float(asset["delivered_kwh"])),
            asset["status"],
        ]
        for asset in scenario["assets"]
    ]
    events = [
        [
            event["time"],
            event["event"],
            event["actor"],
            event["resource"],
            event["status"],
        ]
        for event in scenario["events"]
    ]
    return (
        _status_markdown(scenario),
        _render_kpis(scenario),
        _render_capacity(scenario),
        controls,
        assets,
        events,
        _signals_markdown(scenario),
    )


def build_dashboard():  # pragma: no cover - UI wiring is exercised manually.
    import gradio as gr

    css = """
    .eft-shell {max-width: 1280px; margin: 0 auto;}
    .eft-kpi-grid {
      display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
      gap:12px;margin:8px 0 18px
    }
    .eft-kpi {
      border:1px solid #273449;border-radius:14px;padding:16px;
      background:#0f172a;color:#e2e8f0;
      box-shadow:0 8px 20px rgba(15,23,42,.12)
    }
    .eft-kpi-label,.eft-kpi small {display:block;color:#94a3b8}
    .eft-kpi strong {display:block;font-size:1.6rem;margin:5px 0}
    .eft-kpi.blue {border-top:4px solid #38bdf8}
    .eft-kpi.amber {border-top:4px solid #f59e0b}
    .eft-kpi.green {border-top:4px solid #22c55e}
    .eft-kpi.violet {border-top:4px solid #8b5cf6}
    .eft-kpi.red {border-top:4px solid #ef4444}
    .eft-capacity {
      padding:18px;border:1px solid #cbd5e1;
      border-radius:14px;background:#f8fafc
    }
    .eft-capacity-row {margin-bottom:14px}
    .eft-capacity-label {
      display:flex;justify-content:space-between;
      margin-bottom:5px;color:#334155
    }
    .eft-track {
      height:18px;background:#e2e8f0;border-radius:999px;
      position:relative;overflow:hidden
    }
    .eft-track span {
      position:absolute;left:0;top:0;height:100%;border-radius:999px
    }
    .eft-track .offered {background:#bae6fd}
    .eft-track .reserved {background:#fbbf24}
    .eft-track .dispatched {background:#22c55e}
    .eft-legend {display:flex;gap:22px;font-size:.85rem;color:#475569}
    .eft-legend span:before {
      content:"";display:inline-block;width:10px;height:10px;
      border-radius:50%;margin-right:6px
    }
    .l-offered:before {background:#bae6fd}
    .l-reserved:before {background:#fbbf24}
    .l-dispatched:before {background:#22c55e}
    @media(max-width:760px){.eft-kpi-grid{grid-template-columns:1fr 1fr}}
    """
    names = scenario_names()
    initial = render_scenario(names[0])
    with gr.Blocks(title="Energy Flex Trust Operations", css=css) as dashboard:
        with gr.Column(elem_classes="eft-shell"):
            gr.Markdown(
                "# Energy Flex Trust — Operations Dashboard\n"
                "Read-only views over bundled synthetic coordination snapshots. "
                "No live asset, market, meter, or dispatch connection is used."
            )
            scenario = gr.Dropdown(names, value=names[0], label="Synthetic scenario")
            status = gr.Markdown(initial[0])
            kpis = gr.HTML(initial[1])
            gr.Markdown("### Capacity posture")
            capacity = gr.HTML(initial[2])
            with gr.Tabs():
                with gr.Tab("Trust controls"):
                    controls = gr.Dataframe(
                        headers=["Control", "Status", "Evidence"],
                        value=initial[3],
                        interactive=False,
                    )
                with gr.Tab("Asset operations"):
                    assets = gr.Dataframe(
                        headers=[
                            "Asset",
                            "Type",
                            "Location",
                            "Capacity kW",
                            "Reserved kW",
                            "Dispatched kW",
                            "Delivered kWh",
                            "Status",
                        ],
                        value=initial[4],
                        interactive=False,
                    )
                with gr.Tab("Event timeline"):
                    events = gr.Dataframe(
                        headers=["Time", "Event", "Actor", "Resource", "Status"],
                        value=initial[5],
                        interactive=False,
                    )
            signals = gr.Markdown(initial[6])
            gr.Markdown(
                "---\n**Boundary:** This dashboard visualizes synthetic review "
                "signals. It does not authenticate actors, issue dispatches, "
                "approve settlements, or establish market compliance."
            )
            scenario.change(
                render_scenario,
                inputs=scenario,
                outputs=[status, kpis, capacity, controls, assets, events, signals],
            )
    return dashboard
