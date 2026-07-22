from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.jobs import ExtractedFact, ExtractionRun


def print_extraction_status() -> None:
    with SessionLocal() as session:
        run_count = session.scalar(select(func.count()).select_from(ExtractionRun)) or 0
        fact_count = session.scalar(select(func.count()).select_from(ExtractedFact)) or 0
        print(f"Extraction runs: {run_count}")
        print(f"Extracted facts: {fact_count}")
        rows = session.execute(
            select(ExtractedFact.status, ExtractedFact.fact_type, func.count())
            .group_by(ExtractedFact.status, ExtractedFact.fact_type)
            .order_by(ExtractedFact.status, ExtractedFact.fact_type)
        ).all()
        for status, fact_type, count in rows:
            print(f"{status} {fact_type}: {count}")


if __name__ == "__main__":
    print_extraction_status()
