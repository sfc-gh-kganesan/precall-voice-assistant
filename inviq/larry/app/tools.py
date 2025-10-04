import random


def get_next_submission() -> dict:
    """Retrieve the next submission to process from the InvoiceStore service."""
    return {
        "lift_ticket": "LIFT-12345",
        "submission_id": "3",
        "file_ids": ["id-123", "id-345"],
    }


def extract_fields_from_file(file_id: str) -> dict:
    """Use this tool to extract data fields from an invoice file.

    Args:
      file_id: the file identifier str
    """
    print(f"extracting file {file_id}")
    return {
        "invoice_number": f"foobar-{random.randint(1, 100)}",
        "total_amount": f"${random.randint(200, 3000)}.00",
        "vendor_name": "Shadow Corp",
    }


def create_invoice(submission_id: str, total_amount: str, vendor_name: str, invoice_number: str) -> dict:
    """Use this tool to create a new invoice record using data extracted from an invoice file.

    Args:
      submission_id: the submission this invoice was associated with str
      total_amount: the total_amount field value extracted from the invoice
      vendor_name: the vendor_name field value extracted from the invoice
      invoice_number: the invoice_number field value extracted from the invoice
    """
    return {"success": True, "invoice_id": f"inv-{random.randint(10, 20)}"}


def approve_invoice(invoice_id: str) -> bool:
    """Mark an invoice as approved

    Args:
      invoice_id: the id which identifies the invoice to approve

    Returns:
      true if invoice was successfully approved
      false if something went wrong
    """
    return True


def reject_invoice(invoice_id: str) -> bool:
    """Mark an invoice as rejected

    Args:
      invoice_id: the id which identifies the invoice to reject

    Returns:
      true if invoice was successfully rejected
      false if something went wrong
    """
    return True
