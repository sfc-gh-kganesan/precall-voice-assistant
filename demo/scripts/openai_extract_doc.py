import os
import argparse
from openai import OpenAI
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Extract data from PDF using OpenAI API')
    parser.add_argument('pdf_file_path', help='Path to PDF file')
    
    args = parser.parse_args()
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    pdf_file = Path(args.pdf_file_path)

    try:
        print(f"Uploading file: {pdf_file}")
        
        # 2. Upload the file to OpenAI
        # The 'assistants' purpose is currently required for file uploads
        # that are used with the Chat Completions API.
        uploaded_file = client.files.create(
          file=open(pdf_file, "rb"),
          purpose="user_data"
        )
        
        print(f"File uploaded successfully. File ID: {uploaded_file.id}")

        # 3. Send a request to the model to extract fields
        # We reference the uploaded file using its ID.
        print("Sending request to GPT-4o for data extraction...")
        response = client.responses.create(
            model="gpt-4o",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_file",
                            "file_id": uploaded_file.id,
                        },
                        {
                            "type": "input_text",
                            "text": (
                                """
                                Please extract the following fields from the attached invoice document. Below 
                                are the fields along with a description of the type of data.

                                'snowflake_entity': 'What is the Snowflake entity or company name being billed?',
                                'vendor_name': 'What is the name of the vendor or supplier?',
                                'vendor_address': 'What is the full address of the vendor?',
                                'invoice_number': 'What is the invoice number?',
                                'invoice_date': 'What is the date of the invoice?',
                                'total_amount': 'What is the total amount due on the invoice?',
                                'tax_amount': 'What is the total tax amount (e.g., GST, VAT, Sales Tax)?',
                                'freight_shipping_amount': 'What is the freight or shipping cost?',
                                'invoice_currency': 'What is the currency of the invoice amounts (e.g., USD, EUR, CAD)?',
                                'purchase_order_number': 'What is the Purchase Order (PO) number?',
                                'banking_details': 'What are the banking details or payment instructions provided?',
                                'payment_terms': 'What are the payment terms (e.g., Net 30, Due on receipt)?',
                                'memo_description': 'Is there a memo, description, or summary of charges?',
                                'shipped_to_address': 'What is the ''Shipped To'' or delivery address?',
                                'service_start_date': 'What is the service period start date?',
                                'service_end_date': 'What is the service period end date?',
                                'quantity': 'What are the quantities for the line items listed?',
                                'unit_price': 'What are the unit prices for the line items listed?',
                                'payment_type': 'What is the suggested or required payment type (e.g., Wire, ACH, Check)?',
                                'due_date': 'What is the payment due date?',
                                'vendor_tax_id': 'What is the vendor''s Tax ID, VAT, or GST registration number?',
                                'snowflake_tax_id': 'What is Snowflake''s Tax ID or registration number on the invoice?',
                                'prepaid_flag': 'Is the invoice marked as prepaid or paid in advance?'

                                Return the data in a clean JSON format.
                                """
                            )
                        }
                    ]
                }
            ],
        )

        extracted_data = response
        print("\n--- Full response ---")
        print(extracted_data)
        print("----------------------\n")

        print("\n--- Extracted Data ---")
        print(response.output[0].content[0].text)
        print("----------------------\n")

    except FileNotFoundError:
        print(f"Error: The file was not found at '{pdf_file}'. Please check the path and try again.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()
