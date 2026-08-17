"""HTTP contract smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from energy_flex_trust.api import create_app
from energy_flex_trust.config import Settings
from energy_flex_trust.outbox import OutboxWorker
from energy_flex_trust.ports import NoopDispatchPublisher


def test_health_reports_version() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        )
    )
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.3.0",
        "environment": "test",
    }


def test_missing_development_identity_is_rejected() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/assets",
            json={
                "external_id": "BATTERY-GB-API-NOAUTH",
                "owner_id": "owner-api",
                "asset_type": "battery",
                "capacity_kw": "25",
                "location_code": "GB-LON",
            },
        )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


def test_role_policy_is_enforced_at_api_boundary() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        )
    )
    with TestClient(app) as client:
        response = client.post(
            "/v1/assets",
            headers={
                "X-Actor-ID": "operator-001",
                "X-Actor-Role": "market_operator",
            },
            json={
                "external_id": "BATTERY-GB-API-001",
                "owner_id": "operator-001",
                "asset_type": "battery",
                "capacity_kw": "25",
                "location_code": "GB-LON",
            },
        )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_complete_http_workflow_returns_verifiable_evidence() -> None:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            environment="test",
        )
    )
    owner = {"X-Actor-ID": "owner-api", "X-Actor-Role": "asset_owner"}
    operator = {
        "X-Actor-ID": "operator-api",
        "X-Actor-Role": "market_operator",
    }
    analyst = {
        "X-Actor-ID": "analyst-api",
        "X-Actor-Role": "settlement_analyst",
    }
    auditor = {"X-Actor-ID": "auditor-api", "X-Actor-Role": "auditor"}

    with TestClient(app) as client:
        asset_response = client.post(
            "/v1/assets",
            headers=owner,
            json={
                "external_id": "BATTERY-GB-API-002",
                "owner_id": "owner-api",
                "asset_type": "battery",
                "capacity_kw": "100",
                "location_code": "GB-LON",
            },
        )
        assert asset_response.status_code == 201
        asset_id = asset_response.json()["id"]

        offer_response = client.post(
            "/v1/offers",
            headers=owner,
            json={
                "asset_id": asset_id,
                "window_start": "2026-08-10T18:00:00Z",
                "window_end": "2026-08-10T19:00:00Z",
                "direction": "decrease",
                "quantity_kw": "80",
                "price_per_kwh": "0.50",
            },
        )
        assert offer_response.status_code == 201
        offer_id = offer_response.json()["id"]

        reservation_response = client.post(
            f"/v1/offers/{offer_id}/reservations",
            headers={**operator, "Idempotency-Key": "api-reserve-001"},
            json={"quantity_kw": "50"},
        )
        assert reservation_response.status_code == 201
        reservation_id = reservation_response.json()["id"]

        dispatch_response = client.post(
            f"/v1/reservations/{reservation_id}/dispatches",
            headers={**operator, "Idempotency-Key": "api-dispatch-001"},
            json={
                "target_kw": "40",
                "starts_at": "2026-08-10T18:00:00Z",
                "ends_at": "2026-08-10T19:00:00Z",
            },
        )
        assert dispatch_response.status_code == 201
        assert dispatch_response.json()["status"] == "queued"
        assert dispatch_response.json()["adapter_reference"].startswith("outbox:")

        forbidden_metrics = client.get(
            "/v1/operations/outbox",
            headers=owner,
        )
        assert forbidden_metrics.status_code == 403

        queued_metrics = client.get(
            "/v1/operations/outbox",
            headers=auditor,
        )
        assert queued_metrics.status_code == 200
        assert queued_metrics.json()["pending"] == 1
        assert queued_metrics.json()["dead"] == 0

        delivery = OutboxWorker(
            app.state.session_factory,
            NoopDispatchPublisher(),
        ).run_once(limit=1)
        assert delivery.published == 1

        delivered_metrics = client.get(
            "/v1/operations/outbox",
            headers=operator,
        )
        assert delivered_metrics.status_code == 200
        assert delivered_metrics.json()["pending"] == 0
        assert delivered_metrics.json()["published"] == 1

        reading_response = client.post(
            "/v1/meter-readings",
            headers=owner,
            json={
                "asset_id": asset_id,
                "interval_start": "2026-08-10T18:00:00Z",
                "interval_end": "2026-08-10T19:00:00Z",
                "energy_kwh": "20",
                "source": "synthetic-api-meter",
            },
        )
        assert reading_response.status_code == 201

        settlement_response = client.post(
            f"/v1/reservations/{reservation_id}/settlements",
            headers={**analyst, "Idempotency-Key": "api-settle-001"},
        )
        assert settlement_response.status_code == 201
        settlement_id = settlement_response.json()["id"]
        assert settlement_response.json()["amount"] == "10.000000"

        evidence_response = client.get(
            f"/v1/settlements/{settlement_id}/evidence",
            headers=auditor,
        )
        assert evidence_response.status_code == 200
        assert evidence_response.json()["hash_valid"] is True

        audit_response = client.get("/v1/audit/verify", headers=auditor)
        assert audit_response.status_code == 200
        assert audit_response.json()["valid"] is True
        assert audit_response.json()["event_count"] == 7
