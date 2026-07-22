import json
import re
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx

from app.core.config import Settings
from app.services.extraction_contracts import (
    Evidence,
    ExtractionRequest,
    ProviderExtractionResponse,
    ProviderFact,
)
from app.services.extraction_errors import ExtractionProviderError


class ExtractionProvider(Protocol):
    name: str
    model_name: str

    def extract(self, request: ExtractionRequest) -> ProviderExtractionResponse: ...


class MockExtractionProvider:
    name = "mock"

    def __init__(self, model_name: str = "maintenance-extraction-mock") -> None:
        self.model_name = model_name

    def extract(self, request: ExtractionRequest) -> ProviderExtractionResponse:
        text = request.text
        equipment_tag = (
            request.candidates.equipment_tags[0] if request.candidates.equipment_tags else None
        )
        evidence = Evidence(text=_excerpt(text), page_number=request.first_page_number)
        facts: list[ProviderFact] = []

        for tag in request.candidates.equipment_tags:
            facts.append(
                ProviderFact(
                    fact_type="equipment_mention",
                    equipment_tag=tag,
                    alias=tag,
                    confidence=0.98,
                    evidence=evidence,
                    summary=f"Equipment {tag} is mentioned.",
                )
            )

        lower_text = text.lower()
        work_order_number = _find_work_order(text)
        if work_order_number and equipment_tag:
            facts.append(
                ProviderFact(
                    fact_type="work_order",
                    equipment_tag=equipment_tag,
                    confidence=0.92,
                    evidence=evidence,
                    work_order_number=work_order_number,
                    title=_title(text, "Work order"),
                    description=_excerpt(text, limit=700),
                    status="completed"
                    if "completed" in lower_text or "closed" in lower_text
                    else "open",
                    severity=_severity(lower_text),
                )
            )

        measurement = _find_measurement(text)
        if measurement and equipment_tag:
            metric_name, value, unit = measurement
            facts.append(
                ProviderFact(
                    fact_type="measurement",
                    equipment_tag=equipment_tag,
                    confidence=0.9,
                    evidence=evidence,
                    metric_name=metric_name,
                    metric_value=value,
                    unit=unit,
                    summary=f"{metric_name} measured at {value} {unit}",
                )
            )

        if equipment_tag and any(
            word in lower_text
            for word in ("failure", "failed", "fault", "leak", "trip", "vibration", "alarm")
        ):
            failure_mode = _failure_mode(lower_text)
            facts.append(
                ProviderFact(
                    fact_type="event",
                    equipment_tag=equipment_tag,
                    confidence=0.9,
                    evidence=evidence,
                    event_type="failure",
                    severity=_severity(lower_text),
                    status="closed"
                    if "resolved" in lower_text or "completed" in lower_text
                    else "open",
                    summary=_title(text, "Failure event"),
                    description=_excerpt(text, limit=700),
                )
            )
            facts.append(
                ProviderFact(
                    fact_type="failure_event",
                    equipment_tag=equipment_tag,
                    confidence=0.9,
                    evidence=evidence,
                    failure_mode=failure_mode,
                    failure_mechanism=None,
                    symptoms=_symptoms(lower_text),
                    summary=failure_mode,
                    description=_excerpt(text, limit=700),
                )
            )

        if equipment_tag and any(
            word in lower_text
            for word in (
                "inspect",
                "replace",
                "replaced",
                "repair",
                "calibrate",
                "calibrated",
                "lubricate",
            )
        ):
            facts.append(
                ProviderFact(
                    fact_type="maintenance_action",
                    equipment_tag=equipment_tag,
                    confidence=0.88,
                    evidence=evidence,
                    action_type=_action_type(lower_text),
                    summary=_title(text, "Maintenance action"),
                    description=_excerpt(text, limit=700),
                    status="completed"
                    if "completed" in lower_text or "replaced" in lower_text
                    else "unknown",
                )
            )

        if any(word in lower_text for word in ("procedure", "sop", "lock out", "loto")):
            facts.append(
                ProviderFact(
                    fact_type="procedure",
                    equipment_tag=equipment_tag,
                    confidence=0.86,
                    evidence=evidence,
                    procedure_code=_find_procedure_code(text) or f"PROC-{request.document_code}",
                    revision="unknown",
                    title=_title(text, "Maintenance procedure"),
                    description=_excerpt(text, limit=700),
                    status="active",
                )
            )

        if any(
            word in lower_text for word in ("certificate", "calibration due", "overdue", "required")
        ):
            facts.append(
                ProviderFact(
                    fact_type="compliance_candidate",
                    equipment_tag=equipment_tag,
                    confidence=0.82,
                    evidence=evidence,
                    title=_title(text, "Compliance candidate"),
                    description=_excerpt(text, limit=700),
                )
            )

        return ProviderExtractionResponse(facts=facts, warnings=[])


class OllamaExtractionProvider:
    name = "ollama"

    def __init__(self, *, settings: Settings) -> None:
        self.model_name = settings.extraction_model
        self.base_url = (settings.extraction_api_base_url or settings.ollama_base_url).rstrip("/")
        self.timeout_seconds = settings.extraction_timeout_seconds

    def extract(self, request: ExtractionRequest) -> ProviderExtractionResponse:
        prompt = (
            "Extract industrial maintenance facts as JSON with keys facts and warnings. "
            "Every fact must match the configured schema, include fact_type, confidence, "
            "evidence.text, and avoid secrets or hidden reasoning.\n\n"
            f"Chunk:\n{request.text}"
        )
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("response")
            if not isinstance(content, str):
                raise ValueError("Ollama response did not include JSON text.")
            return ProviderExtractionResponse.model_validate(json.loads(content))
        except Exception as exc:
            raise ExtractionProviderError(details={"provider": self.name}) from exc


def build_extraction_provider(settings: Settings) -> ExtractionProvider:
    if settings.extraction_provider == "mock":
        return MockExtractionProvider(settings.extraction_model)
    if settings.extraction_provider == "ollama":
        return OllamaExtractionProvider(settings=settings)
    raise ExtractionProviderError(details={"provider": settings.extraction_provider})


def _excerpt(text: str, *, limit: int = 360) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:limit] or "No evidence text."


def _title(text: str, fallback: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", _excerpt(text, limit=180))[0].strip()
    return sentence[:255] if sentence else fallback


def _find_work_order(text: str) -> str | None:
    match = re.search(r"\b(?:WO|WORK\s*ORDER)[- #:]*([A-Z0-9-]{3,})\b", text, flags=re.IGNORECASE)
    if match is None:
        return None
    number = match.group(1).upper()
    return number if number.startswith("WO-") else f"WO-{number}"


def _find_procedure_code(text: str) -> str | None:
    match = re.search(r"\b(?:SOP|PROC|PM)[- #:]*([A-Z0-9-]{2,})\b", text, flags=re.IGNORECASE)
    if match is None:
        return None
    prefix = match.group(0).split(match.group(1))[0].replace(" ", "").replace(":", "-")
    return f"{prefix.upper().rstrip('-')}-{match.group(1).upper()}"


def _find_measurement(text: str) -> tuple[str, Decimal, str] | None:
    match = re.search(
        r"\b(pressure|vibration|temperature|speed|flow|reading)?\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s*(psi|bar|mm/s|rpm|c|f|degc|degf)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    try:
        value = Decimal(match.group(2))
    except InvalidOperation:
        return None
    metric_name = (match.group(1) or _metric_from_unit(match.group(3))).lower()
    return metric_name, value, match.group(3).lower()


def _metric_from_unit(unit: str) -> str:
    normalized = unit.lower()
    if normalized in {"psi", "bar"}:
        return "pressure"
    if normalized == "mm/s":
        return "vibration"
    if normalized == "rpm":
        return "speed"
    return "temperature"


def _severity(lower_text: str) -> str:
    if "critical" in lower_text or "shutdown" in lower_text:
        return "critical"
    if "high" in lower_text or "alarm" in lower_text:
        return "high"
    if "low" in lower_text:
        return "low"
    return "medium"


def _failure_mode(lower_text: str) -> str:
    if "seal" in lower_text and "leak" in lower_text:
        return "seal leak"
    if "vibration" in lower_text:
        return "high vibration"
    if "trip" in lower_text:
        return "equipment trip"
    return "equipment failure"


def _symptoms(lower_text: str) -> list[str]:
    symptoms: list[str] = []
    for symptom in ("leak", "vibration", "alarm", "overheat", "noise", "trip"):
        if symptom in lower_text:
            symptoms.append(symptom)
    return symptoms


def _action_type(lower_text: str) -> str:
    for action in ("calibrate", "replace", "repair", "inspect", "lubricate"):
        if action in lower_text:
            return action
    return "maintenance"
