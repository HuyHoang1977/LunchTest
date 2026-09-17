from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .loader import LabLoader


class LabTools:
    def __init__(self, loader: LabLoader) -> None:
        self.loader = loader
        self.repo_root = loader.repo_dir.resolve()

    def list_files(self) -> dict[str, Any]:
        files = self.loader.list_files()
        return {"success": True, "files": files, "count": len(files)}

    def read_file(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        if target is None or not target.is_file():
            return {"success": False, "error": f"File not found: {path}"}
        return {
            "success": True,
            "path": path,
            "content": target.read_text(encoding="utf-8", errors="ignore"),
        }

    def search_code(self, query: str) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for relative in self.loader.list_files():
            if Path(relative).suffix not in {".py", ".md", ".json"}:
                continue
            result = self.read_file(relative)
            content = result.get("content", "")
            if query.lower() in content.lower():
                lines = [
                    number
                    for number, line in enumerate(content.splitlines(), 1)
                    if query.lower() in line.lower()
                ]
                results.append({"file": relative, "match": query, "lines": lines[:10]})
        return {"success": True, "query": query, "results": results}

    def inspect_lab_task(self, task: str) -> dict[str, Any]:
        context = self.loader.load_context()
        matches = []
        for block in context.split("=" * 60):
            if task.lower() in block.lower():
                matches.append(block.strip())
        return {"success": True, "task": task, "matches": matches[:5]}

    def run_command(self, command: str) -> dict[str, Any]:
        allowed = ("python ", "python3 ", "pytest", "pip ")
        if not command.strip().lower().startswith(allowed):
            return {"success": False, "error": "Only read-only Python/test commands are allowed."}
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            return {
                "success": completed.returncode == 0,
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out after 15 seconds."}

    def create_case(self, case: dict[str, Any]) -> dict[str, Any]:
        required = {"type", "difficulty", "phase", "student_action", "expected_consequence", "learning_objective", "next_decision"}
        missing = sorted(required - case.keys())
        if missing:
            return {"success": False, "error": f"Case is missing fields: {', '.join(missing)}"}
        return {"success": True, "case": case}

    def _safe_path(self, path: str) -> Path | None:
        candidate = (self.repo_root / path).resolve()
        try:
            candidate.relative_to(self.repo_root)
        except ValueError:
            return None
        return candidate

    def registry(self) -> dict[str, Callable[..., dict[str, Any]]]:
        return {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "search_code": self.search_code,
            "inspect_lab_task": self.inspect_lab_task,
            "run_command": self.run_command,
            "create_case": self.create_case,
        }

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        function = self.registry().get(name)
        if function is None:
            return {"success": False, "error": f"Unknown tool: {name}"}
        try:
            return function(**arguments)
        except TypeError as error:
            return {"success": False, "error": str(error)}
