from __future__ import annotations

import argparse
from dataclasses import dataclass


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a quick freelance invoice summary.")
    parser.add_argument("--client", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--hourly-rate", type=float, required=True)
    parser.add_argument("--hours", type=float, required=True)
    parser.add_argument("--tax-rate", type=float, default=0.0)
    args = parser.parse_args()

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
