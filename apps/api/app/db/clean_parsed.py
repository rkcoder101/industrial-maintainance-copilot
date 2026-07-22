import shutil
from pathlib import Path

from app.core.config import get_settings


def _is_safe_runtime_dir(path: Path, expected_name: str) -> bool:
    resolved = path.expanduser().resolve()
    unsafe_roots = {Path("/"), Path.home().resolve(), Path("/tmp")}
    return (
        resolved not in unsafe_roots and resolved.name == expected_name and len(resolved.parts) >= 3
    )


def _clean_directory(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True, mode=0o750)
    for child in root.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    settings = get_settings()
    if settings.app_env not in {"development", "test"}:
        raise SystemExit("clean-parsed is only allowed in development or test.")

    parsed_root = settings.parsed_root_path
    rendered_root = settings.rendered_pages_root_path
    if not _is_safe_runtime_dir(parsed_root, "parsed"):
        raise SystemExit(f"Refusing to clean unsafe parsed directory: {parsed_root}")
    if not _is_safe_runtime_dir(rendered_root, "rendered-pages"):
        raise SystemExit(f"Refusing to clean unsafe rendered pages directory: {rendered_root}")

    _clean_directory(parsed_root)
    _clean_directory(rendered_root)
    print(f"Cleaned parsed outputs under {parsed_root} and {rendered_root}")


if __name__ == "__main__":
    main()
