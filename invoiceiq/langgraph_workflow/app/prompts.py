SYSTEM_MESSAGE = """
You are an AI assistant that helps process invoices. You have access to a database to retrieve invoice information.

For each invoice, you will receive the following information:
- invoice metadata extracted from the invoice itself
- purchase order header metadata extracted from the purchase order header
- purchase order line item metadata extracted from the purchase order line items

Your goal is to analyze the invoice and associated information and determine if the invoice should be marked as `approve` or `reject`.

Follow the following business rules when evaluating the invoice:
- If a Purchase Order is not found on the invoice and the total amount on the invoice is greater than $2,000, then reject the invoice.
- If a Purchase Order is not found on the invoice and the total amount is under $2,000, then approve the invoice.
- If the corresponding Purchase Order header is full utilized, then reject the invoice.
- If the corresponding Purchase Order header is closed, then reject the invoice.
- If the corresponding Purchase Order header is listed in "Issued" status, then reject the invoice.
- If the supplier is not the same as the supplier on the Purchase Order header, then reject the invoice.
- If the currency is not the same as the currency on the Purchase Order header, then reject the invoice.
- If the payment terms are not the same as the payment terms on the Purchase Order header, then reject the invoice.
"""

AI_EXTRACT_PROMPT = {
    'vendor_name': 'What is the name of the vendor or supplier?',
    'invoice_number': 'What is the invoice number?',
    'invoice_date': 'What is the date of the invoice?',
    'total_amount': 'What is the total amount due on the invoice?',
    'purchase_order_number': 'What is the Purchase Order (PO) number?',
    'banking_details': 'What are the banking details or payment instructions provided?',
    'payment_terms': 'What are the payment terms (e.g., Net 30, Due on receipt)?',
    'memo_description': 'Is there a memo, description, or summary of charges?',
    'shipped_to_address': 'What is the \'Shipped To\' or delivery address?',
    'service_start_date': 'What is the service period start date?',
    'service_end_date': 'What is the service period end date?',
    'quantity': 'What are the quantities for the line items listed?',
    'unit_price': 'What are the unit prices for the line items listed?',
    'payment_type': 'What is the suggested or required payment type (e.g., Wire, ACH, Check)?',
    'due_date': 'What is the payment due date?',
    'vendor_tax_id': 'What is the vendor\'s Tax ID, VAT, or GST registration number?',
    'snowflake_tax_id': 'What is Snowflake\'s Tax ID or registration number on the invoice?',
    'prepaid_flag': 'Is the invoice marked as prepaid or paid in advance?'
}

HUMAN_MESSAGE_PROMPT = """
INVOICE METADATA:
{ai_extract_metadata}

PURCHASE ORDER HEADER METADATA:
{purchase_order_header_metadata}

PURCHASE ORDER LINE ITEM METADATA:
{purchase_order_line_item_metadata}
"""