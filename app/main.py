from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer


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
        f"Invoice for {invoice[client]} ({invoice[project]})\n"
        f"Work: {invoice[line_item][description]}\n"
        f"Tax: ${invoice[tax]:.2f}\n"
        f"Amount due: ${invoice[total]:.2f}"
    )


class BillstackHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # pragma: no cover
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/health"):
            self._send_json(200, {"status": "ok", "service": "billstack"})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invoice":
            self._send_json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
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
