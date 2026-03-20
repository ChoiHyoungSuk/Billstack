from app.main import InvoiceInput, create_invoice, render_invoice_summary


def test_create_invoice_and_summary():
    invoice = create_invoice(
        InvoiceInput(
            client="Acme Co",
            project="Landing Page",
            hourly_rate=100.0,
            hours=5.5,
            tax_rate=0.1,
        )
    )

    assert invoice["line_item"]["subtotal"] == 550.0
    assert invoice["tax"] == 55.0
    assert invoice["total"] == 605.0

    summary = render_invoice_summary(invoice)
    assert "Invoice for Acme Co (Landing Page)" in summary
    assert "Amount due: $605.00" in summary
