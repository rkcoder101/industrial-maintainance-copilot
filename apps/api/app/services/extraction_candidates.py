import re
from collections.abc import Iterable

from app.models.assets import Equipment
from app.models.documents import Chunk
from app.services.extraction_contracts import ExtractionCandidate

EQUIPMENT_TAG_PATTERN = re.compile(r"\b[A-Z]{1,4}-\d{2,5}[A-Z]?\b")

SIGNAL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "failure": ("failure", "failed", "fault", "leak", "trip", "alarm", "vibration", "overheat"),
    "measurement": ("psi", "bar", "mm/s", "rpm", "celsius", "temperature", "reading", "pressure"),
    "maintenance_action": (
        "inspect",
        "inspection",
        "replace",
        "replaced",
        "repair",
        "calibrate",
        "calibrated",
        "lubricate",
    ),
    "work_order": ("work order", "wo-", "workorder"),
    "procedure": ("procedure", "sop", "step", "lock out", "loto"),
    "compliance_candidate": ("certificate", "calibration due", "overdue", "required"),
}


class CandidateSpottingService:
    def build_candidate(self, chunk: Chunk, equipment: Iterable[Equipment]) -> ExtractionCandidate:
        text = chunk.text_content or ""
        lower_text = text.lower()
        equipment_tags = self._equipment_tags(text, chunk.equipment_hint, equipment)
        signals = [
            signal
            for signal, keywords in SIGNAL_KEYWORDS.items()
            if any(keyword in lower_text for keyword in keywords)
        ]
        eligible = bool(text.strip()) and (bool(equipment_tags) or bool(signals))
        return ExtractionCandidate(
            equipment_tags=equipment_tags,
            signals=signals,
            eligible=eligible,
            reason=None if eligible else "no_maintenance_candidates",
        )

    def _equipment_tags(
        self,
        text: str,
        equipment_hint: str | None,
        equipment: Iterable[Equipment],
    ) -> list[str]:
        seen: dict[str, None] = {}
        for tag in EQUIPMENT_TAG_PATTERN.findall(text.upper()):
            if tag.startswith("WO-"):
                continue
            seen[tag] = None
        if equipment_hint and not equipment_hint.strip().upper().startswith("WO-"):
            seen[equipment_hint.strip().upper()] = None
        upper_text = text.upper()
        for item in equipment:
            if item.equipment_tag.upper() in upper_text:
                seen[item.equipment_tag.upper()] = None
        return list(seen)
