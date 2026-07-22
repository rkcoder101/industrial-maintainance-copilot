from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.assets import EquipmentAlias
from app.models.jobs import ChunkExtractionRun, ExtractedFact, ExtractionRun


class ExtractionRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, run: ExtractionRun) -> ExtractionRun:
        self.session.add(run)
        return run

    def get_by_id(self, run_id: UUID) -> ExtractionRun | None:
        return self.session.get(ExtractionRun, run_id)

    def latest_for_document(self, document_id: UUID) -> ExtractionRun | None:
        return self.session.scalar(
            select(ExtractionRun)
            .where(ExtractionRun.document_id == document_id)
            .order_by(ExtractionRun.started_at.desc(), ExtractionRun.created_at.desc())
            .limit(1)
        )

    def list_for_document(self, document_id: UUID) -> list[ExtractionRun]:
        return list(
            self.session.scalars(
                select(ExtractionRun)
                .where(ExtractionRun.document_id == document_id)
                .order_by(ExtractionRun.started_at.desc(), ExtractionRun.created_at.desc())
            ).all()
        )


class ChunkExtractionRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, run: ChunkExtractionRun) -> ChunkExtractionRun:
        self.session.add(run)
        return run


class ExtractedFactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, fact: ExtractedFact) -> ExtractedFact:
        self.session.add(fact)
        return fact

    def get_by_id(self, fact_id: UUID) -> ExtractedFact | None:
        return self.session.get(ExtractedFact, fact_id)

    def list_for_run(
        self,
        run_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
        status: str | None = None,
        fact_type: str | None = None,
    ) -> tuple[list[ExtractedFact], int]:
        filters = [ExtractedFact.extraction_run_id == run_id]
        if status:
            filters.append(ExtractedFact.status == status)
        if fact_type:
            filters.append(ExtractedFact.fact_type == fact_type)
        total = (
            self.session.scalar(select(func.count()).select_from(ExtractedFact).where(*filters))
            or 0
        )
        items = list(
            self.session.scalars(
                select(ExtractedFact)
                .where(*filters)
                .order_by(ExtractedFact.created_at, ExtractedFact.id)
                .limit(page_size)
                .offset((page - 1) * page_size)
            ).all()
        )
        return items, total


class EquipmentAliasRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, equipment_id: UUID, alias: str) -> EquipmentAlias | None:
        return self.session.scalar(
            select(EquipmentAlias).where(
                EquipmentAlias.equipment_id == equipment_id,
                EquipmentAlias.alias == alias,
            )
        )

    def create(self, alias: EquipmentAlias) -> EquipmentAlias:
        self.session.add(alias)
        return alias
