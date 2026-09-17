from __future__ import annotations

from copy import deepcopy
from typing import Any


class SimulationMemory:
    """State carried between student turns without polluting the system prompt."""

    def __init__(self, lab_id: str = "day03-react-agent") -> None:
        self.state: dict[str, Any] = {
            "lab_id": lab_id,
            "current_phase": "orientation",
            "current_task": None,
            "completed_tasks": [],
            "current_goal": None,
            "student_actions": [],
            "decisions": [],
            "mistakes": [],
            "recoveries": [],
            "hints_used": 0,
            "discovered_files": [],
            "valid_alternatives": [],
            "verification_status": {},
            "current_case": None,
            "generated_cases": [],
        }

    def update(self, **values: Any) -> None:
        self.state.update(values)

    def add_action(self, action: dict[str, Any]) -> None:
        self.state["student_actions"].append(action)

    def add_decision(self, decision: dict[str, Any]) -> None:
        self.state["decisions"].append(decision)

    def add_mistake(self, mistake: dict[str, Any]) -> None:
        self.state["mistakes"].append(mistake)

    def add_recovery(self, recovery: dict[str, Any]) -> None:
        self.state["recoveries"].append(recovery)

    def remember_file(self, path: str) -> None:
        if path not in self.state["discovered_files"]:
            self.state["discovered_files"].append(path)

    def to_dict(self) -> dict[str, Any]:
        return deepcopy(self.state)

    def context(self) -> str:
        return "SIMULATION MEMORY\n" + _format_value(self.state)


def _format_value(value: Any, indent: int = 0) -> str:
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            lines.append(" " * indent + f"{key}: {_format_value(item, indent + 2)}")
        return "\n".join(lines)
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(_format_value(item, indent) for item in value) + "]"
    return repr(value)
