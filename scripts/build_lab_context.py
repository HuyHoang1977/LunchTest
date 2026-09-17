from pathlib import Path

from src.loader import LabLoader


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "data" / "labs" / "day03-react-agent"
    output = LabLoader(root).build_context()
    print(f"Built context: {output}")
