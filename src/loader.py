from __future__ import annotations

from pathlib import Path


class LabLoader:
    def __init__(self, lab_dir: str | Path) -> None:
        self.lab_dir = Path(lab_dir).resolve()
        self.repo_dir = self.lab_dir / "repo"
        self.context_file = self.lab_dir / "lab_context.md"

    def build_context(self) -> Path:
        parts: list[str] = []
        for path in sorted(self.lab_dir.rglob("*.md")):
            if path == self.context_file or ".git" in path.parts:
                continue
            relative_path = path.relative_to(self.lab_dir).as_posix()
            parts.append(
                "\n".join(
                    [
                        "=" * 60,
                        f"FILE: {relative_path}",
                        "=" * 60,
                        path.read_text(encoding="utf-8", errors="ignore"),
                    ]
                )
            )
        output = "\n\n".join(parts)
        self.context_file.write_text(output + "\n", encoding="utf-8")
        return self.context_file

    def load_context(self) -> str:
        if not self.context_file.exists():
            self.build_context()
        return self.context_file.read_text(encoding="utf-8", errors="ignore")

    def list_files(self) -> list[str]:
        if not self.repo_dir.exists():
            return []
        return sorted(
            path.relative_to(self.repo_dir).as_posix()
            for path in self.repo_dir.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )
