"""FastAPI application factory."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import __version__
from .config import Settings
from .database import build_engine, build_session_factory, initialize_database
from .domain import Actor, ActorRole
from .errors import DomainError
from .schemas import (
    AssetCreate,
    AssetRead,
    AuditVerificationRead,
    DispatchCreate,
    DispatchRead,
    EvidenceRead,
    HealthRead,
    MeterReadingCreate,
    MeterReadingRead,
    OfferCreate,
    OfferRead,
    ReservationCreate,
    ReservationRead,
    SettlementRead,
)
from .service import CoordinationService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)
    initialize_database(engine)

    application = FastAPI(
        title="Energy Flex Trust Platform",
        version=__version__,
        description=(
            "Secure reference API for auditable energy-flexibility coordination. "
            "The default dispatch adapter never contacts a live asset."
        ),
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory

    def get_session() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_actor(
        actor_id: Annotated[str, Header(alias="X-Actor-ID")],
        actor_role: Annotated[ActorRole, Header(alias="X-Actor-Role")],
    ) -> Actor:
        return Actor(actor_id=actor_id, role=actor_role)

    SessionDependency = Annotated[Session, Depends(get_session)]
    ActorDependency = Annotated[Actor, Depends(get_actor)]
    IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key")]

    @application.exception_handler(DomainError)
    async def domain_error_handler(_request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @application.get("/health", response_model=HealthRead, tags=["system"])
    def health() -> HealthRead:
        return HealthRead(
            status="ok",
            version=__version__,
            environment=settings.environment,
        )

    @application.post(
        "/v1/assets",
        response_model=AssetRead,
        status_code=status.HTTP_201_CREATED,
        tags=["assets"],
    )
    def register_asset(
        command: AssetCreate,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> AssetRead:
        resource = CoordinationService(session).register_asset(command, actor)
        return AssetRead.model_validate(resource)

    @application.post(
        "/v1/offers",
        response_model=OfferRead,
        status_code=status.HTTP_201_CREATED,
        tags=["offers"],
    )
    def create_offer(
        command: OfferCreate,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> OfferRead:
        resource = CoordinationService(session).create_offer(command, actor)
        return OfferRead.model_validate(resource)

    @application.post(
        "/v1/offers/{offer_id}/reservations",
        response_model=ReservationRead,
        status_code=status.HTTP_201_CREATED,
        tags=["coordination"],
    )
    def reserve_offer(
        offer_id: str,
        command: ReservationCreate,
        idempotency_key: IdempotencyKey,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> ReservationRead:
        resource = CoordinationService(session).reserve_offer(
            offer_id,
            command,
            actor,
            idempotency_key,
        )
        return ReservationRead.model_validate(resource)

    @application.post(
        "/v1/reservations/{reservation_id}/dispatches",
        response_model=DispatchRead,
        status_code=status.HTTP_201_CREATED,
        tags=["coordination"],
    )
    def issue_dispatch(
        reservation_id: str,
        command: DispatchCreate,
        idempotency_key: IdempotencyKey,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> DispatchRead:
        resource = CoordinationService(session).issue_dispatch(
            reservation_id,
            command,
            actor,
            idempotency_key,
        )
        return DispatchRead.model_validate(resource)

    @application.post(
        "/v1/meter-readings",
        response_model=MeterReadingRead,
        status_code=status.HTTP_201_CREATED,
        tags=["evidence"],
    )
    def record_meter_reading(
        command: MeterReadingCreate,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> MeterReadingRead:
        resource = CoordinationService(session).record_meter_reading(command, actor)
        return MeterReadingRead.model_validate(resource)

    @application.post(
        "/v1/reservations/{reservation_id}/settlements",
        response_model=SettlementRead,
        status_code=status.HTTP_201_CREATED,
        tags=["evidence"],
    )
    def settle_reservation(
        reservation_id: str,
        idempotency_key: IdempotencyKey,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> SettlementRead:
        resource = CoordinationService(session).settle_reservation(
            reservation_id,
            actor,
            idempotency_key,
        )
        return SettlementRead.model_validate(resource)

    @application.get(
        "/v1/settlements/{settlement_id}/evidence",
        response_model=EvidenceRead,
        tags=["evidence"],
    )
    def settlement_evidence(
        settlement_id: str,
        session: SessionDependency,
        actor: ActorDependency,
    ) -> EvidenceRead:
        evidence = CoordinationService(session).settlement_evidence(
            settlement_id,
            actor,
        )
        return EvidenceRead.model_validate(evidence)

    @application.get(
        "/v1/audit/verify",
        response_model=AuditVerificationRead,
        tags=["audit"],
    )
    def verify_audit(
        session: SessionDependency,
        actor: ActorDependency,
    ) -> AuditVerificationRead:
        result = CoordinationService(session).audit_verification(actor)
        return AuditVerificationRead.model_validate(result)

    return application


app = create_app()
