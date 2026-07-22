from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ScanResult:
    status: str
    message: str | None = None


class FileScanner(Protocol):
    async def scan(self, path: Path) -> ScanResult: ...


class NoopFileScanner:
    async def scan(self, path: Path) -> ScanResult:
        _ = path
        return ScanResult(
            status="scanner_not_configured",
            message="Malware scanning is not active in Phase 3.",
        )
