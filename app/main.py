from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class InvoiceInput:
    client: str
    project: str
    hourly_rate: float
    hours: float
    tax_rate: float = 0.0


def create_invoice(data: InvoiceInput) -> dict:
    subtotal = round(data.hourly_rate * data.hours, 2)
    tax = round(subtotal * data.tax_rate, 2)
    total = round(subtotal + tax, 2)

    return {
        "client": data.client,
        "project": data.project,
        "line_item": {
            "description": f"{data.hours:.2f}h @ ${data.hourly_rate:.2f}/h",
            "subtotal": subtotal,
        },
        "tax": tax,
        "total": total,
    }


def render_invoice_summary(invoice: dict) -> str:
    return (
        f"Invoice for {invoice['client']} ({invoice['project']})\n"
        f"Work: {invoice['line_item']['description']}\n"
        f"Tax: ${invoice['tax']:.2f}\n"
        f"Amount due: ${invoice['total']:.2f}"
    )


LANDING_HTML = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Billstack</title>
    <style>
      :root {
        --bg: #f7fafc;
        --card: #ffffff;
        --line: #e2e8f0;
        --text: #1f2937;
        --muted: #6b7280;
        --accent: #0f766e;
        --accent-dark: #115e59;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;
        color: var(--text);
        background: radial-gradient(circle at top, #e6fffa 0%, var(--bg) 35%, var(--bg) 100%);
      }
      .wrap {
        max-width: 920px;
        margin: 0 auto;
        padding: 24px 16px 48px;
      }
      .hero {
        margin-bottom: 16px;
      }
      .hero h1 {
        margin: 0 0 6px;
        font-size: 2rem;
      }
      .hero p {
        margin: 0;
        color: var(--muted);
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }
      @media (min-width: 900px) {
        .grid { grid-template-columns: 1.1fr 0.9fr; }
      }
      .card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 16px;
      }
      .card h2 {
        margin: 0 0 10px;
        font-size: 1.1rem;
      }
      .row {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        margin-bottom: 10px;
      }
      @media (min-width: 640px) {
        .row.two { grid-template-columns: 1fr 1fr; }
      }
      label {
        display: block;
        font-size: 0.88rem;
        color: var(--muted);
        margin-bottom: 4px;
      }
      input {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 10px;
        font-size: 0.95rem;
      }
      .actions {
        display: flex;
        gap: 10px;
        margin-top: 8px;
      }
      button {
        border: 0;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
        cursor: pointer;
      }
      .primary {
        background: var(--accent);
        color: #fff;
      }
      .primary:hover { background: var(--accent-dark); }
      .ghost {
        background: #eef2f7;
        color: #374151;
      }
      .result {
        white-space: pre-wrap;
        min-height: 140px;
        margin-top: 12px;
        padding: 12px;
        border: 1px dashed var(--line);
        border-radius: 10px;
        background: #f8fafc;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.9rem;
      }
      .ok { color: #065f46; }
      .err { color: #991b1b; }
      .meta ul { margin: 0; padding-left: 20px; }
      .meta li { margin: 4px 0; color: #374151; }
      .endpoint {
        margin-top: 10px;
        color: var(--muted);
        font-size: 0.9rem;
      }
      code {
        background: #f1f5f9;
        padding: 0.15rem 0.35rem;
        border-radius: 6px;
      }
    </style>
  </head>
  <body>
    <main class=\"wrap\">
      <section class=\"hero\">
        <h1>Billstack</h1>
        <p>Freelancer invoice summary prototype. Enter values and preview the result instantly.</p>
      </section>

      <section class=\"grid\">
        <article class=\"card\">
          <h2>Invoice Preview</h2>
          <form id=\"invoice-form\" method=\"post\" action=\"/invoice\">
            <div class=\"row two\">
              <div>
                <label for=\"client\">Client</label>
                <input id=\"client\" name=\"client\" value=\"Acme Co\" required />
              </div>
              <div>
                <label for=\"project\">Project</label>
                <input id=\"project\" name=\"project\" value=\"Landing Page\" required />
              </div>
            </div>
            <div class=\"row two\">
              <div>
                <label for=\"hourly_rate\">Hourly Rate (USD)</label>
                <input id=\"hourly_rate\" name=\"hourly_rate\" type=\"number\" min=\"0\" step=\"0.01\" value=\"100\" required />
              </div>
              <div>
                <label for=\"hours\">Hours</label>
                <input id=\"hours\" name=\"hours\" type=\"number\" min=\"0\" step=\"0.01\" value=\"5.5\" required />
              </div>
            </div>
            <div class=\"row\">
              <div>
                <label for=\"tax_rate\">Tax Rate (0.1 = 10%)</label>
                <input id=\"tax_rate\" name=\"tax_rate\" type=\"number\" min=\"0\" step=\"0.01\" value=\"0.1\" required />
              </div>
            </div>
            <div class=\"actions\">
              <button class=\"primary\" type=\"submit\">Generate Summary</button>
              <button class=\"ghost\" type=\"button\" id=\"fill-sample\">Use Sample</button>
            </div>
          </form>
          <div id=\"status\" class=\"endpoint\">Ready</div>
          <pre id=\"result\" class=\"result\">Run the form to preview invoice output.</pre>
        </article>

        <aside class=\"card meta\">
          <h2>API Endpoints</h2>
          <ul>
            <li><code>GET /health</code> - service status</li>
            <li><code>POST /invoice</code> - invoice summary JSON</li>
          </ul>
          <p class=\"endpoint\">Tip: Share this page to collect fast feedback on output format and pricing UX.</p>
        </aside>
      </section>
    </main>

    <script>
      const form = document.getElementById('invoice-form');
      const resultEl = document.getElementById('result');
      const statusEl = document.getElementById('status');
      const fillSampleBtn = document.getElementById('fill-sample');

      fillSampleBtn.addEventListener('click', () => {
        document.getElementById('client').value = 'Orbit Studio';
        document.getElementById('project').value = 'Website Redesign';
        document.getElementById('hourly_rate').value = '120';
        document.getElementById('hours').value = '8';
        document.getElementById('tax_rate').value = '0.1';
      });

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        statusEl.textContent = 'Submitting...';
        resultEl.textContent = 'Loading...';
        resultEl.classList.remove('ok', 'err');

        const payload = {
          client: document.getElementById('client').value.trim(),
          project: document.getElementById('project').value.trim(),
          hourly_rate: Number(document.getElementById('hourly_rate').value),
          hours: Number(document.getElementById('hours').value),
          tax_rate: Number(document.getElementById('tax_rate').value),
        };

        try {
          const response = await fetch('/invoice', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const data = await response.json();

          if (!response.ok) {
            statusEl.textContent = `Failed (${response.status})`;
            resultEl.textContent = JSON.stringify(data, null, 2);
            resultEl.classList.add('err');
            return;
          }

          statusEl.textContent = `Success (${response.status})`;
          resultEl.textContent = data.summary + '\\n\\n' + JSON.stringify(data.invoice, null, 2);
          resultEl.classList.add('ok');
        } catch (error) {
          statusEl.textContent = 'Network error';
          resultEl.textContent = String(error);
          resultEl.classList.add('err');
        }
      });
    </script>
  </body>
</html>
"""


class BillstackHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict, *, write_body: bool = True) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.wfile.write(body)

    def _send_html(self, status: int, html: str, *, write_body: bool = True) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # pragma: no cover
        return

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(200, LANDING_HTML)
            return
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "billstack"})
            return
        self._send_json(404, {"error": "not_found"})

    def do_HEAD(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(200, LANDING_HTML, write_body=False)
            return
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "billstack"}, write_body=False)
            return
        self._send_json(404, {"error": "not_found"}, write_body=False)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/invoice":
            self._send_json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            content_type = str(self.headers.get("Content-Type") or "").lower()

            if raw and "application/x-www-form-urlencoded" in content_type:
                form = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
                payload = {key: values[0] if values else "" for key, values in form.items()}
            else:
                payload = json.loads(raw.decode("utf-8")) if raw else {}

            data = InvoiceInput(
                client=str(payload["client"]),
                project=str(payload["project"]),
                hourly_rate=float(payload["hourly_rate"]),
                hours=float(payload["hours"]),
                tax_rate=float(payload.get("tax_rate", 0.0)),
            )
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send_json(400, {"error": "invalid_payload", "detail": str(exc)})
            return

        invoice = create_invoice(data)
        self._send_json(200, {"invoice": invoice, "summary": render_invoice_summary(invoice)})


def run_server() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), BillstackHandler)
    print(f"Billstack server listening on :{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Billstack invoice service")
    parser.add_argument("--serve", action="store_true", help="Run HTTP server for deployment")
    parser.add_argument("--client")
    parser.add_argument("--project")
    parser.add_argument("--hourly-rate", type=float)
    parser.add_argument("--hours", type=float)
    parser.add_argument("--tax-rate", type=float, default=0.0)
    args = parser.parse_args()

    if args.serve:
        run_server()
        return

    required = [args.client, args.project, args.hourly_rate, args.hours]
    if any(value is None for value in required):
        raise SystemExit("CLI mode requires --client --project --hourly-rate --hours")

    invoice = create_invoice(
        InvoiceInput(
            client=args.client,
            project=args.project,
            hourly_rate=args.hourly_rate,
            hours=args.hours,
            tax_rate=args.tax_rate,
        )
    )
    print(render_invoice_summary(invoice))


if __name__ == "__main__":
    main()
