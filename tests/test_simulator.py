import json
from pathlib import Path

from src.agent import SimulatorAgent
from src.loader import LabLoader
from src.providers import OfflineProvider
from src.tools import LabTools


ROOT = Path(__file__).parents[1]
LAB_DIR = ROOT / "data" / "labs" / "day03-react-agent"


def test_context_excludes_generated_context_and_includes_vlearn():
    loader = LabLoader(LAB_DIR)
    context_path = loader.build_context()
    context = context_path.read_text(encoding="utf-8")
    assert "FILE: vlearn.md" in context
    assert "FILE: lab_context.md" not in context


def test_tools_prevent_path_escape():
    tools = LabTools(LabLoader(LAB_DIR))
    result = tools.read_file("../../../../Windows/System32/drivers/etc/hosts")
    assert result["success"] is False


def test_offline_agent_runs_tool_and_returns_case():
    agent = SimulatorAgent(LabLoader(LAB_DIR), OfflineProvider())
    result = agent.run_turn("Hãy list các file trong repo")
    assert result["case"]["type"] == "NORMAL_PROGRESS"
    assert agent.trace[0]["action"]["tool"] == "list_files"


def test_trace_is_json_serializable(tmp_path):
    agent = SimulatorAgent(LabLoader(LAB_DIR), OfflineProvider())
    agent.run_turn("Tìm dispatcher trong source")
    output = tmp_path / "trace.json"
    agent.write_trace(str(output))
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload[0]["observation"]["success"] is True


def test_case_choice_is_reviewed_and_next_case_is_created():
    agent = SimulatorAgent(LabLoader(LAB_DIR), OfflineProvider())
    first = agent.run_turn("Tôi bắt đầu code ReAct Agent luôn")
    assert [option["id"] for option in first["case"]["options"]] == ["A", "B", "C"]
    result = agent.run_turn("A")
    assert result["review"]["correct"] is True
    assert result["case"]["options"]
    assert agent.memory.state["decisions"][-1]["choice"] == "A"


def test_wrong_case_choice_is_recorded_as_mistake():
    agent = SimulatorAgent(LabLoader(LAB_DIR), OfflineProvider())
    agent.run_turn("Tôi bắt đầu code ReAct Agent luôn")
    result = agent.run_turn("B")
    assert result["review"]["correct"] is False
    assert agent.memory.state["mistakes"][-1]["choice"] == "B"


def test_generate_cases_uses_multiple_lab_tools():
    agent = SimulatorAgent(LabLoader(LAB_DIR), OfflineProvider())
    cases = agent.generate_cases(6)
    assert len(cases) == 6
    assert {entry["action"]["tool"] for entry in agent.trace} == {
        "list_files", "inspect_lab_task", "search_code", "read_file"
    }
    assert all(case["options"] and case["answer"] == "A" for case in cases)
