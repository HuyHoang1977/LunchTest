from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .app import create_agent


HTML = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AB Simulator</title>
<style>
:root { color-scheme: light; font-family: Georgia, 'Times New Roman', serif; background: #f4f1ea; color: #172321; }
body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 15% 10%, #e4eee8, transparent 35%), #f4f1ea; }
main { width: min(920px, calc(100% - 32px)); margin: 0 auto; padding: 48px 0 72px; }
.eyebrow { color: #b44d32; font: 700 12px/1.2 ui-sans-serif, system-ui, sans-serif; letter-spacing: .12em; text-transform: uppercase; }
h1 { max-width: 680px; margin: 12px 0 10px; font-size: clamp(38px, 7vw, 72px); line-height: .95; font-weight: 500; }
.lede { max-width: 620px; color: #53625d; font: 16px/1.6 ui-sans-serif, system-ui, sans-serif; }
.panel { margin-top: 32px; padding: 28px; border: 1px solid #d6d8ce; border-radius: 8px; background: rgba(255,255,255,.68); box-shadow: 0 16px 50px rgba(35,49,41,.08); }
label { display: block; margin-bottom: 10px; font: 700 13px ui-sans-serif, system-ui, sans-serif; }
textarea { width: 100%; box-sizing: border-box; min-height: 96px; padding: 14px; border: 1px solid #bdc9c0; border-radius: 6px; resize: vertical; background: #fffdf8; color: inherit; font: 16px/1.45 ui-sans-serif, system-ui, sans-serif; }
button { border: 0; border-radius: 6px; cursor: pointer; font: 700 14px ui-sans-serif, system-ui, sans-serif; }
.primary { margin-top: 14px; padding: 13px 18px; background: #b44d32; color: white; }
.primary:hover { background: #8f3927; }
#case { display: none; }
.case-head { display: flex; justify-content: space-between; gap: 16px; align-items: start; }
.case-type { color: #b44d32; font: 700 12px ui-sans-serif, system-ui, sans-serif; letter-spacing: .08em; }
h2 { margin: 8px 0 8px; font-size: 27px; font-weight: 500; }
.case-text { color: #53625d; font: 15px/1.55 ui-sans-serif, system-ui, sans-serif; }
.options { display: grid; gap: 10px; margin-top: 22px; }
.option { display: grid; grid-template-columns: 36px 1fr; gap: 12px; width: 100%; padding: 15px; text-align: left; border: 1px solid #c6d0c8; background: #fffdf8; color: #172321; }
.option:hover:not(:disabled) { border-color: #b44d32; transform: translateY(-1px); }
.option:disabled { cursor: default; opacity: .65; }
.option-key { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: #e4eee8; color: #245545; }
#review { display: none; margin-top: 22px; padding: 16px; border-left: 4px solid #245545; background: #e8f1eb; font: 15px/1.5 ui-sans-serif, system-ui, sans-serif; }
#review.wrong { border-color: #b44d32; background: #f8e9e3; }
.next { margin-top: 8px; color: #53625d; }
.status { min-height: 24px; margin-top: 12px; color: #b44d32; font: 13px ui-sans-serif, system-ui, sans-serif; }
</style>
</head>
<body>
<main>
<div class="eyebrow">Day 03 / ReAct Agent</div>
<h1>AB Simulator</h1>
<p class="lede">Chọn hướng xử lý như trong một buổi lab thật. Mỗi quyết định sẽ được review và mở ra tình huống tiếp theo.</p>
<section class="panel" id="start">
<label for="message">Bạn đang định làm gì?</label>
<textarea id="message" placeholder="Ví dụ: Tôi bắt đầu code ReAct Agent luôn"></textarea>
<button class="primary" id="startButton">Tạo tình huống</button>
<div class="status" id="status"></div>
</section>
<section class="panel" id="case">
<div class="case-head"><div><div class="case-type" id="type"></div><h2 id="title">Chọn một hướng đi</h2></div></div>
<div class="case-text" id="objective"></div>
<div class="options" id="options"></div>
<div id="review"></div>
</section>
</main>
<script>
const start = document.querySelector('#start');
const casePanel = document.querySelector('#case');
const status = document.querySelector('#status');
const review = document.querySelector('#review');
const options = document.querySelector('#options');

function showCase(payload) {
  const current = payload.case;
  casePanel.style.display = 'block';
  document.querySelector('#type').textContent = current.type.replaceAll('_', ' ');
  document.querySelector('#objective').textContent = current.learning_objective;
  options.innerHTML = '';
  review.style.display = 'none';
  current.options.forEach(option => {
    const button = document.createElement('button');
    button.className = 'option';
    button.innerHTML = `<span class="option-key">${option.id}</span><span>${option.label}</span>`;
    button.addEventListener('click', () => choose(option.id));
    options.appendChild(button);
  });
  casePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function send(message) {
  status.textContent = 'Đang mô phỏng...';
  const response = await fetch('/turn', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message}) });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Không thể xử lý lượt này');
  status.textContent = '';
  return payload;
}

document.querySelector('#startButton').addEventListener('click', async () => {
  const message = document.querySelector('#message').value.trim();
  if (!message) { status.textContent = 'Hãy mô tả hành động đầu tiên.'; return; }
  try { showCase(await send(message)); } catch (error) { status.textContent = error.message; }
});

async function choose(id) {
  document.querySelectorAll('.option').forEach(button => button.disabled = true);
  try {
    const payload = await send(id);
    const result = payload.review;
    review.className = result.correct ? '' : 'wrong';
    review.innerHTML = `<strong>${result.correct ? 'Lựa chọn phù hợp' : 'Lựa chọn cần xem lại'}</strong><br>${payload.text}<div class="next"><strong>Hướng tiếp theo:</strong> ${result.next_direction}</div>`;
    review.style.display = 'block';
    setTimeout(() => showCase(payload), 1200);
  } catch (error) {
    status.textContent = error.message;
    document.querySelectorAll('.option').forEach(button => button.disabled = false);
  }
}
</script>
</body>
</html>"""


class SimulatorHandler(BaseHTTPRequestHandler):
    agent = create_agent()

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(404)
            return
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/turn":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload: dict[str, Any] = json.loads(self.rfile.read(length))
            result = self.agent.run_turn(str(payload.get("message", "")))
            self._json(200, result)
        except Exception as error:
            self._json(400, {"error": str(error)})

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), SimulatorHandler)
    print("AB Simulator web UI: http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
