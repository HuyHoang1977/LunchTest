from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .agent import SimulatorAgent
    from .loader import LabLoader
    from .providers import get_provider
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.agent import SimulatorAgent
    from src.loader import LabLoader
    from src.providers import get_provider


ROOT = Path(__file__).resolve().parents[1]
LAB_DIR = ROOT / "data" / "labs" / "day03-react-agent"
TRACE_PATH = ROOT / "docs" / "trace_waterfall.json"
CASES_PATH = ROOT / "data" / "generated_cases.json"


def create_agent() -> SimulatorAgent:
    loader = LabLoader(LAB_DIR)
    loader.build_context()
    return SimulatorAgent(loader, get_provider())


def main() -> None:
    parser = argparse.ArgumentParser(description="AB Simulator MVP")
    parser.add_argument("--message", help="Run one simulation turn")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--build-context", action="store_true")
    parser.add_argument("--generate-cases", type=int, metavar="N", help="Generate N Lab cases through multiple tool calls")
    args = parser.parse_args()

    loader = LabLoader(LAB_DIR)
    if args.build_context:
        print(f"Built: {loader.build_context()}")
        return

    agent = create_agent()
    if args.generate_cases:
        cases = agent.generate_cases(args.generate_cases)
        CASES_PATH.parent.mkdir(parents=True, exist_ok=True)
        CASES_PATH.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"count": len(cases), "path": str(CASES_PATH), "cases": cases}, ensure_ascii=False, indent=2))
    elif args.message:
        print(json.dumps(agent.run_turn(args.message), ensure_ascii=False, indent=2))
    elif args.interactive:
        print("AB Simulator offline-ready. Type 'exit' to stop.")
        while True:
            message = input("student> ").strip()
            if message.lower() in {"exit", "quit"}:
                break
            print(json.dumps(agent.run_turn(message), ensure_ascii=False, indent=2))
    else:
        print("Use --message, --interactive, --generate-cases N, or --build-context.")
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    agent.write_trace(str(TRACE_PATH))


if __name__ == "__main__":
    main()
