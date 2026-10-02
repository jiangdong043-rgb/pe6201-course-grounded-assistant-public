"""Local browser interface for the PE6201 Raw/RAG demonstration."""

from __future__ import annotations

import argparse
import json
import os
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from generation import OpenRouterClient, build_retriever, load_json, run_condition
from presentation_results import load_presentation, PRESENTATION_DIR


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PE6201 Course Grounded Assistant</title>
  <style>
    :root { --navy:#17365d; --blue:#4472c4; --orange:#ed7d31; --ink:#202124; --muted:#68717d; --line:#d9e1f2; --bg:#f5f7fb; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--bg); font-family:Arial, Helvetica, sans-serif; }
    .shell { max-width:1220px; margin:0 auto; padding:34px 28px 48px; }
    header { display:flex; justify-content:space-between; gap:24px; align-items:flex-start; margin-bottom:24px; }
    h1 { color:var(--navy); font-size:34px; margin:0 0 7px; letter-spacing:-.4px; }
    .subtitle { color:var(--muted); font-size:17px; margin:0; }
    .status { background:#fff; border:1px solid var(--line); border-radius:12px; padding:12px 16px; min-width:235px; box-shadow:0 3px 14px rgba(23,54,93,.06); }
    .status b { display:block; color:var(--navy); margin-bottom:5px; }
    .dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; background:#999; }
    .dot.ok { background:#2e8b57; }
    .panel { background:#fff; border:1px solid var(--line); border-radius:16px; padding:22px; box-shadow:0 7px 24px rgba(23,54,93,.07); }
    label { display:block; color:var(--navy); font-weight:700; margin-bottom:9px; }
    textarea { width:100%; min-height:92px; resize:vertical; padding:15px; border:1px solid #b8c5d8; border-radius:10px; font:16px/1.45 Arial; color:var(--ink); outline:none; }
    textarea:focus { border-color:var(--blue); box-shadow:0 0 0 3px rgba(68,114,196,.12); }
    .actions { display:flex; align-items:center; gap:12px; margin-top:13px; flex-wrap:wrap; }
    button { border:0; border-radius:9px; padding:11px 18px; font-size:15px; font-weight:700; cursor:pointer; }
    #ask { background:var(--navy); color:white; min-width:175px; }
    #ask:hover { background:#214977; }
    #ask:disabled { opacity:.55; cursor:wait; }
    .example { background:#eef3fa; color:var(--navy); font-weight:600; }
    .example:hover { background:#e1eaf6; }
    .hint { color:var(--muted); font-size:13px; margin-left:auto; }
    .results { display:grid; grid-template-columns:1fr 1fr; gap:18px; margin-top:20px; }
    .card { background:#fff; border:1px solid var(--line); border-radius:16px; overflow:hidden; box-shadow:0 7px 24px rgba(23,54,93,.06); min-height:270px; }
    .card-head { display:flex; align-items:center; justify-content:space-between; padding:15px 19px; color:white; }
    .raw .card-head { background:var(--orange); }
    .rag .card-head { background:var(--blue); }
    .card-head h2 { margin:0; font-size:21px; }
    .tag { background:rgba(255,255,255,.2); border:1px solid rgba(255,255,255,.45); border-radius:999px; padding:4px 9px; font-size:12px; }
    .card-body { padding:19px; }
    .answer { font-size:16px; line-height:1.55; min-height:105px; white-space:pre-wrap; }
    .empty { color:#8a929d; }
    .metrics { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:17px; }
    .metric { background:#f6f8fb; border-radius:9px; padding:9px 10px; }
    .metric span { display:block; color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.45px; }
    .metric b { display:block; margin-top:4px; color:var(--navy); font-size:14px; }
    .sources { margin-top:15px; padding-top:14px; border-top:1px solid #e7ebf2; }
    .sources h3 { font-size:13px; color:var(--navy); text-transform:uppercase; letter-spacing:.45px; margin:0 0 8px; }
    .chip { display:inline-block; background:#eaf1fb; color:#244f86; border:1px solid #cbdcf2; border-radius:999px; padding:5px 9px; margin:0 6px 6px 0; font-size:12px; }
    .warning { margin-top:20px; color:#5f6368; background:#fff; border:1px solid var(--line); border-radius:12px; padding:13px 16px; font-size:13px; line-height:1.4; }
    .summary { margin-top:20px; background:#fff; border:1px solid var(--line); border-radius:16px; padding:21px; box-shadow:0 7px 24px rgba(23,54,93,.06); }
    .summary h2 { color:var(--navy); margin:0 0 15px; font-size:21px; }
    .summary table { border-collapse:collapse; width:100%; margin:15px 0; font-size:15px; }
    .summary th,.summary td { padding:11px 9px; border-bottom:1px solid var(--line); text-align:left; }
    .summary th { background:#eef3fa; color:var(--navy); }
    .summary p { line-height:1.5; font-size:14px; }
    .summary-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
    .summary-item { background:#f6f8fb; border-radius:10px; padding:13px; }
    .summary-item span { color:var(--muted); display:block; font-size:12px; margin-bottom:5px; }
    .summary-item b { color:var(--navy); font-size:20px; }
    .summary-links { margin-top:15px; }
    .summary-links a { display:inline-block; color:var(--navy); background:#eaf1fb; border:1px solid #cbdcf2; text-decoration:none; border-radius:8px; padding:8px 12px; margin-right:8px; font-weight:700; font-size:13px; }
    .error { color:#9c2f24; background:#fff0ee; border:1px solid #efc6c1; border-radius:9px; padding:12px; }
    .spinner { display:none; width:16px; height:16px; border:2px solid rgba(255,255,255,.45); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; vertical-align:-3px; margin-right:8px; }
    @keyframes spin { to { transform:rotate(360deg); } }
    @media (max-width:820px) { header{flex-direction:column}.results{grid-template-columns:1fr}.summary-grid{grid-template-columns:1fr 1fr}.status{width:100%}.hint{width:100%;margin-left:0} }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div><h1>PE6201 Course Grounded Assistant</h1><p class="subtitle">Same model, two conditions: Raw knowledge versus retrieved course evidence</p></div>
      <div class="status"><b>Local demonstration</b><span id="statusDot" class="dot"></span><span id="statusText">Checking setup...</span></div>
    </header>
    <section class="panel">
      <label for="question">Ask a PE6201 question</label>
      <textarea id="question">What is the revised final-project submission date?</textarea>
      <div class="actions">
        <button id="ask"><span class="spinner" id="spinner"></span><span id="askText">Compare Raw and RAG</span></button>
        <button class="example" data-q="What percentage of the PE6201 course grade is the End-of-Course Project worth?">Requirement example</button>
        <button class="example" data-q="What exact submission time applies to the revised 4 October final-project deadline?">Abstention test</button>
        <span class="hint">Live calls use OpenRouter and may take a few seconds.</span>
      </div>
    </section>
    <section class="results">
      <article class="card raw"><div class="card-head"><h2>Raw model</h2><span class="tag">No retrieval</span></div><div class="card-body" id="rawBody"><div class="answer empty">Run a comparison to see the model answer without course documents.</div></div></article>
      <article class="card rag"><div class="card-head"><h2>RAG model</h2><span class="tag">Top 5 course passages</span></div><div class="card-body" id="ragBody"><div class="answer empty">Run a comparison to see the answer grounded in retrieved PE6201 sources.</div></div></article>
    </section>
    <section class="summary">
      __RESULTS_SUMMARY__
      <div class="summary-links"><a href="/assets/accuracy" target="_blank">Open strict completeness by category</a><a href="/assets/tradeoff" target="_blank">Open scoring and API measurements</a></div>
    </section>
    <div class="warning"><b>Responsible use:</b> NTULearn and instructor announcements remain authoritative. Prompts request caution, but refusal and citation entailment are not enforced by code. Verify missing or conflicting details. API latency excludes retrieval and browser time; API cost excludes embeddings, hosting and review. Live comparisons are separate from the saved experiment.</div>
  </main>
  <script>
    const $ = id => document.getElementById(id);
    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
    function render(result) {
      const citations = result.cited_sources || [];
      const citationHtml = citations.length ? citations.map(c => `<span class="chip">${esc(c)}</span>`).join('') : '<span class="empty">No course citation</span>';
      return `<div class="answer">${esc(result.answer)}</div>
        <div class="metrics"><div class="metric"><span>API latency</span><b>${Number(result.latency_seconds).toFixed(2)} s</b></div><div class="metric"><span>Tokens</span><b>${result.total_tokens}</b></div><div class="metric"><span>API cost</span><b>$${Number(result.cost_usd).toFixed(6)}</b></div></div>
        <div class="sources"><h3>${result.condition === 'rag' ? 'Course sources' : 'Sources'}</h3>${citationHtml}</div>`;
    }
    async function health() {
      try { const r=await fetch('/api/health'); const h=await r.json(); $('statusDot').className='dot '+(h.ready?'ok':''); $('statusText').textContent=h.ready?'Ready (local setup checked)':h.message; }
      catch { $('statusText').textContent='Local server unavailable'; }
    }
    async function ask() {
      const q=$('question').value.trim(); if(!q) return;
      $('ask').disabled=true; $('spinner').style.display='inline-block'; $('askText').textContent='Running comparison...';
      $('rawBody').innerHTML='<div class="answer empty">Waiting for the Raw response...</div>'; $('ragBody').innerHTML='<div class="answer empty">Retrieving evidence and generating the RAG response...</div>';
      try {
        const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})}); const payload=await r.json();
        if(!r.ok) throw new Error(payload.error||'Request failed');
        $('rawBody').innerHTML=render(payload.raw); $('ragBody').innerHTML=render(payload.rag);
      } catch(e) { const h=`<div class="error">${esc(e.message)}</div>`; $('rawBody').innerHTML=h; $('ragBody').innerHTML=h; }
      finally { $('ask').disabled=false; $('spinner').style.display='none'; $('askText').textContent='Compare Raw and RAG'; }
    }
    $('ask').addEventListener('click',ask); $('question').addEventListener('keydown',e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey))ask()});
    document.querySelectorAll('.example').forEach(b=>b.addEventListener('click',()=>{$('question').value=b.dataset.q;$('question').focus()}));
    health();
  </script>
</body>
</html>"""


def render_page(project: Path) -> str:
    data = load_presentation(project)
    review = data['review']['overall']
    experiment = data['experiment']['conditions']
    rows = ''.join(
        f'<tr><td>{label}</td><td>{review["raw"][key]}/40</td><td>{review["rag"][key]}/40</td></tr>'
        for label, key in (
            ('Historical provisional answer score', 'original_answer_score'),
            ('Post-hoc strict completeness', 'strict_completeness_score'),
            ('Post-hoc page-citation support', 'page_citation_support_score'),
            ('Strict complete AND page-supported', 'strict_complete_and_cited'),
        )
    )
    summary = f'''<h2>Saved experiment and AI-assisted review</h2>
      <p>40 questions, 80 saved answers. AI-assisted, unblinded, post-hoc review; <b>not human-validated</b>.</p>
      <table><thead><tr><th>Scoring interpretation</th><th>Raw</th><th>RAG</th></tr></thead><tbody>{rows}</tbody></table>
      <p>These are different interpretations of the same outputs, not new model runs. Strict completeness requires every frozen required fact; some requirements exceed the question wording. Missing detail is not always factual error. The prompts also differ between conditions.</p>
      <div class="summary-grid">
        <div class="summary-item"><span>Raw API cost / 1,000 questions</span><b>${experiment['raw']['projected_cost_per_1000_questions_usd']:.4f}</b></div>
        <div class="summary-item"><span>RAG API cost / 1,000 questions</span><b>${experiment['rag']['projected_cost_per_1000_questions_usd']:.4f}</b></div>
        <div class="summary-item"><span>Raw mean API request time</span><b>{experiment['raw']['average_latency_seconds']:.3f} s</b></div>
        <div class="summary-item"><span>RAG mean API request time</span><b>{experiment['rag']['average_latency_seconds']:.3f} s</b></div>
      </div>'''
    return HTML.replace('__RESULTS_SUMMARY__', summary)


class AppState:
    def __init__(self, project: Path):
        self.project = project
        self.model_settings = load_json(project / "config/model_settings.json")
        self.retrieval_settings = load_json(project / "config/retrieval_settings.json")
        self._retriever = None
        self._lock = threading.Lock()

    @property
    def retriever(self):
        with self._lock:
            if self._retriever is None:
                self._retriever = build_retriever(self.project, self.retrieval_settings)
            return self._retriever

    def health(self) -> dict:
        key_name = self.model_settings["api_key_environment_variable"]
        chunks = self.project / self.retrieval_settings["chunks"]
        cache = self.project / self.retrieval_settings["embedding_cache"]
        ready = bool(os.getenv(key_name)) and chunks.exists() and cache.exists()
        if not os.getenv(key_name):
            message = f"Missing {key_name}"
        elif not chunks.exists() or not cache.exists():
            message = "Retrieval data is missing"
        else:
            message = "Ready"
        return {"ready": ready, "message": message, "model": self.model_settings["model"]}

    def ask(self, question: str) -> dict:
        client = OpenRouterClient(self.model_settings)
        raw = run_condition(client, self.model_settings, question, "raw")
        rag = run_condition(
            client,
            self.model_settings,
            question,
            "rag",
            retriever=self.retriever,
            top_k=self.retrieval_settings["top_k"],
        )
        return {"raw": asdict(raw), "rag": asdict(rag)}


def make_handler(state: AppState):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, payload: dict, status=HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/":
                body = render_page(state.project).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/health":
                self.send_json(state.health())
            elif self.path in {"/assets/accuracy", "/assets/tradeoff"}:
                filename = "strict_completeness_by_category.png" if self.path.endswith("accuracy") else "scoring_cost_api_latency.png"
                asset = state.project / PRESENTATION_DIR / filename
                if not asset.exists():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                body = asset.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path != "/api/ask":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                question = str(payload.get("question", "")).strip()
                if not question or len(question) > 1000:
                    self.send_json({"error": "Enter a question between 1 and 1,000 characters."}, HTTPStatus.BAD_REQUEST)
                    return
                self.send_json(state.ask(question))
            except Exception as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def log_message(self, format: str, *args) -> None:
            print(f"{self.client_address[0]} {format % args}")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    state = AppState(args.project.resolve())
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    print(f"PE6201 demo running at http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
