# AB Simulator MVP

MVP mô phỏng môi trường Lab 3 `Chatbot vs ReAct Agent` bằng Markdown Context + Memory + multi-turn Tool Calling. Repo Lab gốc được đặt tại `data/labs/day03-react-agent/repo`.

## Chạy nhanh

Yêu cầu Python 3.10+.

```powershell
python -m pytest -q
python -m src.app --build-context
python -m src.app --message "Hãy list các file trong repo"
python -m src.app --interactive
python -m src.app --generate-cases 10
```

Để người dùng bấm lựa chọn bằng giao diện web:

```powershell
python -m src.web
```

Mở trình duyệt tại `http://127.0.0.1:8000`. Nhập hành động đầu tiên, bấm **Tạo tình huống**, rồi bấm trực tiếp vào các nút lựa chọn. Sau mỗi lần bấm, giao diện hiển thị review đúng/sai và hướng đi tiếp theo.

Mặc định dùng `OfflineProvider`, không cần API key. Muốn dùng OpenAI, đặt `OPENAI_API_KEY` trước khi chạy; agent sẽ gửi system prompt, lab context, simulation memory và lịch sử hội thoại tới model. Không đưa toàn bộ source vào prompt: model dùng `list_files`, `read_file`, `search_code`, `inspect_lab_task`, `run_command` và `create_case` khi cần.

## Luồng case lựa chọn

Mỗi lượt đầu tiên tạo một case có các lựa chọn `A/B/C`. Gõ lựa chọn ở prompt `student>`:

```text
student> Tôi bắt đầu code ReAct Agent luôn
student> A
```

Simulator sẽ trả review gồm `correct`, hành động đã chọn và hướng đi tiếp theo. Lựa chọn sai được lưu vào `memory.mistakes`; lựa chọn đúng được lưu vào `memory.decisions`. Có thể nhập `A`, `B`, `C` hoặc `1`, `2`, `3`.

## Sinh nhiều case bằng nhiều lượt tool

Lệnh `--generate-cases N` chạy một tool plan gồm `list_files`, `inspect_lab_task`, `search_code` và `read_file`, sau đó tạo tối đa `N` case dựa trên observation của repo. Kết quả được lưu tại [data/generated_cases.json](data/generated_cases.json). Ví dụ:

```powershell
python -m src.app --generate-cases 20
```

Các case hiện bao phủ Agentic Fit, Tool Schema, Dispatcher, ReAct Loop, Failure Recovery, Valid Alternative, Verification và Reflection.

## Cấu trúc

- `data/labs/day03-react-agent/vlearn.md`: nội dung hướng dẫn VLearn đã chuẩn hóa.
- `data/labs/day03-react-agent/lab_context.md`: được tạo từ mọi Markdown, bỏ qua chính nó.
- `src/loader.py`: nạp Lab và build context.
- `src/memory.py`: state giữa các lượt.
- `src/tools.py`: sáu tools MVP với giới hạn path và command.
- `src/agent.py`: vòng lặp tối đa 8 lượt tool call và trace.
- `src/providers.py`: offline provider và OpenAI adapter.
- `docs/trace_waterfall.json`: trace được ghi sau mỗi lần chạy CLI.
