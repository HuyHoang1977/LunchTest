# Trace Evaluation

File `docs/trace_waterfall.json` được tạo bởi `python -m src.app --message "..."`.

## MVP checks

- Context loader thu thập Markdown từ repo Lab và `vlearn.md`.
- Source code chỉ được đọc on-demand qua tools.
- Memory giữ lại hành động, file đã phát hiện, lỗi và case hiện tại.
- Trace ghi timestamp, round, action và observation.
- Offline provider dùng để kiểm thử không cần API key.

Khi nghiệm thu với LLM thật, đặt `OPENAI_API_KEY`, chạy nhiều lượt hội thoại và dán các trace tiêu biểu vào báo cáo này.
