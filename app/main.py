from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from structlog.contextvars import bind_contextvars

from .agent import LabAgent
from .incidents import disable, enable, status
from .logging_config import configure_logging, get_logger
from .metrics import record_error, snapshot
from .middleware import CorrelationIdMiddleware
from .pii import hash_user_id, summarize_text
from .schemas import ChatRequest, ChatResponse
from .tracing import tracing_enabled

configure_logging()
log = get_logger()
app = FastAPI(title="Day 13 Observability Lab")
app.add_middleware(CorrelationIdMiddleware)
agent = LabAgent()


@app.on_event("startup")
async def startup() -> None:
    log.info(
        "app_started",
        service=os.getenv("APP_NAME", "day13-observability-lab"),
        env=os.getenv("APP_ENV", "dev"),
        payload={"tracing_enabled": tracing_enabled()},
    )


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "tracing_enabled": tracing_enabled(), "incidents": status()}


@app.get("/metrics")
async def metrics() -> dict:
    return snapshot()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Day 13 Observability Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1b1f24;
      --muted: #69707d;
      --line: #d8dde6;
      --accent: #1870f0;
      --ok: #14853d;
      --warn: #b26a00;
      --bad: #c62828;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }
    h1 { margin: 0; font-size: 22px; font-weight: 700; }
    .meta { color: var(--muted); font-size: 13px; text-align: right; }
    main {
      max-width: 1180px;
      margin: 0 auto;
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }
    .panel {
      min-height: 172px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .panel h2 {
      margin: 0 0 12px;
      font-size: 15px;
      font-weight: 700;
    }
    .value { font-size: 34px; line-height: 1; font-weight: 700; }
    .unit { color: var(--muted); font-size: 13px; margin-top: 6px; }
    .rows { display: grid; gap: 8px; }
    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      font-size: 14px;
    }
    .bar {
      height: 8px;
      border-radius: 999px;
      background: #e9edf3;
      overflow: hidden;
      margin-top: 12px;
    }
    .fill { height: 100%; background: var(--accent); width: 0%; }
    .threshold {
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      border-top: 1px dashed var(--line);
      padding-top: 8px;
    }
    .status-ok { color: var(--ok); }
    .status-warn { color: var(--warn); }
    .status-bad { color: var(--bad); }
    @media (max-width: 860px) {
      header { align-items: flex-start; flex-direction: column; }
      .meta { text-align: left; }
      .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Day 13 Observability Dashboard</h1>
    <div class="meta">
      <div>Default range: last 1 hour</div>
      <div>Auto refresh: 20 seconds</div>
      <div id="last-updated">Waiting for metrics...</div>
    </div>
  </header>
  <main>
    <section class="grid" aria-label="Observability panels">
      <article class="panel">
        <h2>Latency P50/P95/P99</h2>
        <div class="rows">
          <div class="row"><span>P50</span><strong id="lat-p50">0 ms</strong></div>
          <div class="row"><span>P95</span><strong id="lat-p95">0 ms</strong></div>
          <div class="row"><span>P99</span><strong id="lat-p99">0 ms</strong></div>
        </div>
        <div class="threshold">SLO: P95 &lt; 3000 ms</div>
      </article>
      <article class="panel">
        <h2>Traffic</h2>
        <div class="value" id="traffic">0</div>
        <div class="unit">requests in this process</div>
        <div class="threshold">Source: /metrics traffic counter</div>
      </article>
      <article class="panel">
        <h2>Error Rate</h2>
        <div class="value" id="error-rate">0%</div>
        <div class="unit" id="error-breakdown">No errors</div>
        <div class="threshold">SLO: error rate &lt; 2%</div>
      </article>
      <article class="panel">
        <h2>Cost</h2>
        <div class="value" id="cost-total">$0.0000</div>
        <div class="unit" id="cost-avg">$0.0000 average per request</div>
        <div class="threshold">Budget: &lt; $2.50 per day</div>
      </article>
      <article class="panel">
        <h2>Tokens In/Out</h2>
        <div class="rows">
          <div class="row"><span>Input</span><strong id="tokens-in">0</strong></div>
          <div class="row"><span>Output</span><strong id="tokens-out">0</strong></div>
        </div>
        <div class="threshold">Units: tokens</div>
      </article>
      <article class="panel">
        <h2>Quality Proxy</h2>
        <div class="value" id="quality">0.00</div>
        <div class="unit">heuristic average score</div>
        <div class="bar"><div class="fill" id="quality-fill"></div></div>
        <div class="threshold">Target: quality_avg &gt;= 0.75</div>
      </article>
    </section>
  </main>
  <script>
    const fmtMs = value => `${Number(value || 0).toFixed(0)} ms`;
    const fmtMoney = value => `$${Number(value || 0).toFixed(4)}`;
    const setText = (id, value) => { document.getElementById(id).textContent = value; };

    async function refreshMetrics() {
      const response = await fetch('/metrics', { cache: 'no-store' });
      const data = await response.json();
      const traffic = Number(data.traffic || 0);
      const errors = Object.values(data.error_breakdown || {}).reduce((sum, item) => sum + Number(item || 0), 0);
      const errorRate = traffic > 0 ? (errors / traffic) * 100 : 0;
      const quality = Number(data.quality_avg || 0);

      setText('lat-p50', fmtMs(data.latency_p50));
      setText('lat-p95', fmtMs(data.latency_p95));
      setText('lat-p99', fmtMs(data.latency_p99));
      setText('traffic', String(traffic));
      setText('error-rate', `${errorRate.toFixed(2)}%`);
      setText('error-breakdown', errors ? JSON.stringify(data.error_breakdown) : 'No errors');
      setText('cost-total', fmtMoney(data.total_cost_usd));
      setText('cost-avg', `${fmtMoney(data.avg_cost_usd)} average per request`);
      setText('tokens-in', String(data.tokens_in_total || 0));
      setText('tokens-out', String(data.tokens_out_total || 0));
      setText('quality', quality.toFixed(2));
      document.getElementById('quality-fill').style.width = `${Math.max(0, Math.min(100, quality * 100))}%`;
      document.getElementById('quality').className = `value ${quality >= 0.75 ? 'status-ok' : 'status-warn'}`;
      document.getElementById('error-rate').className = `value ${errorRate < 2 ? 'status-ok' : 'status-bad'}`;
      setText('last-updated', `Last updated: ${new Date().toLocaleTimeString()}`);
    }

    refreshMetrics().catch(error => setText('last-updated', `Metrics error: ${error.message}`));
    setInterval(() => refreshMetrics().catch(error => setText('last-updated', `Metrics error: ${error.message}`)), 20000);
  </script>
</body>
</html>
        """
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    bind_contextvars(
        user_id_hash=hash_user_id(body.user_id),
        session_id=body.session_id,
        feature=body.feature,
        model=agent.model,
        env=os.getenv("APP_ENV", "dev"),
    )
    
    log.info(
        "request_received",
        service="api",
        payload={"message_preview": summarize_text(body.message)},
    )
    try:
        result = agent.run(
            user_id=body.user_id,
            feature=body.feature,
            session_id=body.session_id,
            message=body.message,
        )
        log.info(
            "response_sent",
            service="api",
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            payload={"answer_preview": summarize_text(result.answer)},
        )
        return ChatResponse(
            answer=result.answer,
            correlation_id=request.state.correlation_id,
            latency_ms=result.latency_ms,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
            cost_usd=result.cost_usd,
            quality_score=result.quality_score,
        )
    except Exception as exc:  # pragma: no cover
        error_type = type(exc).__name__
        record_error(error_type)
        log.error(
            "request_failed",
            service="api",
            error_type=error_type,
            payload={"detail": str(exc), "message_preview": summarize_text(body.message)},
        )
        raise HTTPException(status_code=500, detail=error_type) from exc


@app.post("/incidents/{name}/enable")
async def enable_incident(name: str) -> JSONResponse:
    try:
        enable(name)
        log.warning("incident_enabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/incidents/{name}/disable")
async def disable_incident(name: str) -> JSONResponse:
    try:
        disable(name)
        log.warning("incident_disabled", service="control", payload={"name": name})
        return JSONResponse({"ok": True, "incidents": status()})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
