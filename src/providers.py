from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ProviderResponse:
    text: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class OfflineProvider:
    """Deterministic provider for local development and tests."""

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderResponse:
        if any(message.get("role") == "tool" for message in messages):
            return ProviderResponse(
                text="Mình đã nhận observation từ tool. Hãy dùng kết quả này để chọn bước tiếp theo hoặc kiểm tra một file cụ thể."
            )
        user_messages = [message["content"] for message in messages if message.get("role") == "user"]
        user_message = user_messages[-1].lower() if user_messages else ""
        if "list" in user_message or "repo" in user_message or "file" in user_message:
            return ProviderResponse(tool_calls=[{"name": "list_files", "arguments": {}}])
        if "dispatcher" in user_message or "tool" in user_message:
            return ProviderResponse(tool_calls=[{"name": "search_code", "arguments": {"query": "dispatch_tool_call"}}])
        return ProviderResponse(
            text="Mình đã ghi nhận quyết định của bạn. Hãy chọn bước kiểm tra tiếp theo trong repo hoặc mô tả thay đổi bạn muốn thực hiện."
        )


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderResponse:
        payload = json.dumps({"model": self.model, "messages": messages, "tools": tools}).encode()
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode())
        message = data["choices"][0]["message"]
        calls = [
            {"name": call["function"]["name"], "arguments": json.loads(call["function"]["arguments"])}
            for call in message.get("tool_calls", [])
        ]
        return ProviderResponse(text=message.get("content"), tool_calls=calls)


def get_provider() -> OfflineProvider | OpenAIProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return OpenAIProvider(api_key, os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    return OfflineProvider()
