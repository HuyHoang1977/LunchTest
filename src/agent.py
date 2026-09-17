from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from .loader import LabLoader
from .memory import SimulationMemory
from .prompts import build_messages
from .providers import ProviderResponse
from .tools import LabTools


class SimulatorAgent:
    def __init__(self, loader: LabLoader, provider: Any, max_tool_rounds: int = 8) -> None:
        self.loader = loader
        self.provider = provider
        self.tools = LabTools(loader)
        self.memory = SimulationMemory()
        self.max_tool_rounds = max_tool_rounds
        self.conversation: list[dict[str, Any]] = []
        self.trace: list[dict[str, Any]] = []

    def run_turn(self, user_message: str) -> dict[str, Any]:
        pending_case = self.memory.state.get("current_case")
        if pending_case and pending_case.get("options"):
            return self._review_choice(user_message, pending_case)

        self.memory.add_action({"message": user_message})
        messages = build_messages(self.loader.load_context(), self.memory.context(), user_message)
        messages.extend(self.conversation)
        for round_number in range(1, self.max_tool_rounds + 1):
            response: ProviderResponse = self.provider.generate(messages, self.tool_schemas())
            if response.text:
                self.conversation.extend([
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": response.text},
                ])
                case = self._case_for(user_message, response.text)
                self.memory.update(current_case=case, current_goal=case["next_decision"])
                return {"text": response.text, "case": self._public_case(case), "rounds": round_number}
            tool_calls = response.tool_calls or []
            if not tool_calls:
                return {"text": "Agent không trả về kết quả hợp lệ.", "case": self._fallback_case(user_message), "rounds": round_number}
            for call in tool_calls:
                name = call["name"]
                arguments = call.get("arguments", {})
                result = self.tools.execute(name, arguments)
                self._record_trace(round_number, name, arguments, result)
                if name in {"read_file", "search_code"} and result.get("success"):
                    if name == "read_file":
                        self.memory.remember_file(arguments.get("path", ""))
                messages.append({"role": "assistant", "tool_calls": [call]})
                messages.append({"role": "tool", "name": name, "content": json.dumps(result, ensure_ascii=False)})
        return {"text": "Agent đã đạt giới hạn số vòng gọi tool.", "case": self._fallback_case(user_message), "rounds": self.max_tool_rounds}

    def tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {"name": "list_files", "description": "List files in the Lab repository", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read one repository file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "search_code", "description": "Search source and documentation", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "inspect_lab_task", "description": "Find a task in Lab documentation", "parameters": {"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}}},
            {"type": "function", "function": {"name": "run_command", "description": "Run a safe read-only project command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
            {"type": "function", "function": {"name": "create_case", "description": "Validate a simulation case", "parameters": {"type": "object", "properties": {}, "additionalProperties": True}}},
        ]

    def write_trace(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(self.trace, file, ensure_ascii=False, indent=2)

    def generate_cases(self, count: int = 6) -> list[dict[str, Any]]:
        """Inspect the Lab through several tool turns, then create grounded cases."""
        observations = []
        tool_plan = [
            ("list_files", {}),
            ("inspect_lab_task", {"task": "TASK 1.1"}),
            ("inspect_lab_task", {"task": "TASK 2.2"}),
            ("search_code", {"query": "dispatch_tool_call"}),
            ("search_code", {"query": "MAX_ITERATIONS"}),
            ("read_file", {"path": "src/app.py"}),
        ]
        for round_number, (name, arguments) in enumerate(tool_plan, 1):
            result = self.tools.execute(name, arguments)
            self._record_trace(round_number, name, arguments, result)
            observations.append({"tool": name, "result": result})

        cases = self._build_case_catalog(observations)
        return cases[:max(1, count)]

    def _build_case_catalog(self, observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        evidence_files = sorted({
            item["file"]
            for observation in observations
            for item in observation["result"].get("results", [])
            if "file" in item
        })
        evidence = ", ".join(evidence_files[:4]) or "repo Lab"
        return [
            self._generated_case("case_agentic_fit", "DECISION_POINT", "orientation", "Tôi bắt đầu code ngay", "Đánh giá Agentic Fit và đọc checkpoint trước khi chọn kiến trúc.", evidence),
            self._generated_case("case_tool_schema", "WRONG_DECISION", "task_1_2", "Tôi khai báo tool nhưng bỏ required parameters", "Schema thiếu required field có thể làm tool call không hợp lệ.", evidence),
            self._generated_case("case_dispatcher", "WRONG_DECISION", "task_2_1", "Tôi gọi sai tên tool trong dispatcher", "Đối chiếu tên tool với registry và schema trước khi dispatch.", evidence),
            self._generated_case("case_react_loop", "PREMATURE_ACTION", "task_2_2", "LLM trả tool_call xong tôi return luôn", "Phải thực thi tool, đưa Observation trở lại LLM rồi mới kết luận.", evidence),
            self._generated_case("case_failure_recovery", "FAILURE_RECOVERY", "task_3_1", "Lệnh test bị lỗi nhưng tôi vẫn ghi pass", "Đọc traceback và chạy lại kiểm tra nhỏ trước khi cập nhật trace.", evidence),
            self._generated_case("case_valid_alternative", "VALID_ALTERNATIVE", "task_2_1", "Tôi đọc source trước rồi quay lại hoàn thiện task", "Workflow khác thứ tự vẫn hợp lệ nếu đạt learning objective và có bằng chứng.", evidence),
            self._generated_case("case_verification", "VERIFICATION", "task_3_1", "Tôi kiểm tra trace_waterfall.json", "Xác nhận trace có Thought, Action, Observation và latency trước khi nộp.", evidence),
            self._generated_case("case_reflection", "REFLECTION", "task_3_2", "Tôi giải thích vì sao chọn ReAct Agent", "Liên hệ quyết định kiến trúc với nhu cầu multi-step và tool use.", evidence),
        ]

    def _generated_case(self, case_id: str, case_type: str, phase: str, action: str, consequence: str, evidence: str) -> dict[str, Any]:
        options = [
            {"id": "A", "label": "Kiểm tra tài liệu và bằng chứng liên quan trước", "correct": True},
            {"id": "B", "label": "Tiếp tục bỏ qua checkpoint và đoán kết quả", "correct": False},
            {"id": "C", "label": "Chỉ sửa biểu hiện bên ngoài mà không kiểm tra nguyên nhân", "correct": False},
        ]
        return {
            "case_id": case_id,
            "type": case_type,
            "difficulty": 2,
            "phase": phase,
            "student_action": action,
            "expected_consequence": consequence,
            "learning_objective": "Ra quyết định dựa trên bằng chứng của Lab và phục hồi sau sai lầm.",
            "evidence": evidence,
            "options": [{key: value for key, value in option.items() if key != "correct"} for option in options],
            "answer": "A",
            "next_decision": "Bạn sẽ inspect file nào hoặc chạy kiểm tra nào tiếp theo?",
        }

    def _record_trace(self, round_number: int, name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        self.trace.append({
            "timestamp": datetime.now(UTC).isoformat(),
            "round": round_number,
            "action": {"tool": name, "arguments": arguments},
            "observation": result,
        })

    def _case_for(self, message: str, response: str) -> dict[str, Any]:
        lowered = message.lower()
        case_type = "NORMAL_PROGRESS"
        if any(word in lowered for word in ("code luôn", "implement ngay", "bắt đầu code")):
            case_type = "PREMATURE_ACTION"
        elif "lỗi" in lowered or "error" in lowered:
            case_type = "FAILURE_RECOVERY"
        elif "hint" in lowered or "gợi ý" in lowered:
            case_type = "HINT_REQUEST"
        options = self._options_for(case_type)
        return {
            "type": case_type,
            "difficulty": 1,
            "phase": self.memory.state["current_phase"],
            "student_action": message,
            "expected_consequence": response,
            "learning_objective": "Understand ReAct decisions, tool evidence, and recovery paths.",
            "next_decision": "Chọn một hướng đi để tiếp tục mô phỏng.",
            "options": options,
            "_answer_keys": [option["id"] for option in options if option["correct"]],
        }

    def _fallback_case(self, message: str) -> dict[str, Any]:
        return self._case_for(message, "Không có observation mới; hãy chọn một hành động tiếp theo.")

    def _options_for(self, case_type: str) -> list[dict[str, Any]]:
        if case_type == "PREMATURE_ACTION":
            return [
                {"id": "A", "label": "Đọc LAB-GUIDE.md và xác định checkpoint trước", "correct": True},
                {"id": "B", "label": "Code ReAct loop ngay rồi sửa lỗi sau", "correct": False},
                {"id": "C", "label": "Bỏ qua yêu cầu và chỉ chạy chatbot baseline", "correct": False},
            ]
        if case_type == "FAILURE_RECOVERY":
            return [
                {"id": "A", "label": "Đọc traceback, xác định file gây lỗi rồi chạy lại test nhỏ", "correct": True},
                {"id": "B", "label": "Xóa toàn bộ thay đổi và chạy lại ngẫu nhiên", "correct": False},
                {"id": "C", "label": "Bỏ qua lỗi và ghi kết quả là thành công", "correct": False},
            ]
        return [
            {"id": "A", "label": "Đọc tài liệu/checkpoint liên quan trước", "correct": True},
            {"id": "B", "label": "Đọc đúng source file liên quan bằng search_code/read_file", "correct": True},
            {"id": "C", "label": "Sửa code ngay mà không kiểm tra yêu cầu", "correct": False},
        ]

    def _review_choice(self, user_message: str, case: dict[str, Any]) -> dict[str, Any]:
        choice = self._normalize_choice(user_message)
        valid_ids = {option["id"] for option in case["options"]}
        if choice not in valid_ids:
            return {
                "text": "Mình chưa nhận ra lựa chọn. Hãy trả lời bằng A, B, C hoặc 1, 2, 3.",
                "case": self._public_case(case),
                "review": {"correct": None, "message": "Lựa chọn không hợp lệ."},
            }

        selected = next(option for option in case["options"] if option["id"] == choice)
        correct = choice in case["_answer_keys"]
        review_message = (
            "Lựa chọn phù hợp với mục tiêu hiện tại."
            if correct
            else "Lựa chọn này có thể làm bạn bỏ qua một checkpoint hoặc tạo lỗi khó quan sát."
        )
        decision = {"case_type": case["type"], "choice": choice, "correct": correct}
        self.memory.add_decision(decision)
        if correct:
            self.memory.state["completed_tasks"].append(case["phase"])
        else:
            self.memory.add_mistake({"case_type": case["type"], "choice": choice, "reason": review_message})
        self.memory.update(current_case=None, current_goal=selected["label"])
        next_case = self._case_for(
            f"Student chọn {choice}: {selected['label']}",
            "Tiếp tục sang checkpoint kế tiếp sau phần review.",
        )
        self.memory.update(current_case=next_case, current_goal=next_case["next_decision"])
        return {
            "text": review_message,
            "review": {
                "choice": choice,
                "correct": correct,
                "selected_action": selected["label"],
                "next_direction": next_case["next_decision"],
            },
            "case": self._public_case(next_case),
        }

    @staticmethod
    def _normalize_choice(value: str) -> str:
        normalized = value.strip().upper()
        if normalized[:2] in {"A.", "B.", "C."}:
            return normalized[0]
        if normalized in {"1", "2", "3"}:
            return {"1": "A", "2": "B", "3": "C"}[normalized]
        return normalized

    @staticmethod
    def _public_case(case: dict[str, Any]) -> dict[str, Any]:
        return {
            key: [
                {option_key: option_value for option_key, option_value in option.items() if option_key != "correct"}
                for option in value
            ]
            if key == "options" else value
            for key, value in case.items()
            if key != "_answer_keys"
        }
