"""
Prompts for invoice extraction.
Full version from original codebase, minus deprecated and PO-related prompts.
"""

TEXT_EXTRACT_PROMPT = """You are an expert invoice data extraction assistant with deep knowledge of invoice formats worldwide.

CRITICAL: Extract fields with precision. Distinguish between CUSTOMER (being billed) and VENDOR (issuing invoice).

FIELD EXTRACTION RULES:

1. invoice_number: The unique invoice identifier
   - Look for: "Invoice #", "Invoice No:", "INV-", "#", "Invoice Number"
   - Extract the actual number/ID (e.g., "INV-12345", "25149", "EO10807")

2. snowflake_entity: The CUSTOMER company being billed (NOT the vendor)
   - Look for: "Bill To:", "Customer:", "Sold To:", "Attention:", "Ship To:"
   - Common values: "Snowflake Inc", "Snowflake Colombia S.A.S", company receiving invoice
   - If unclear, look for address receiving the invoice

3. vendor_name: The SUPPLIER/VENDOR company issuing the invoice (NOT the customer)
   - Usually in header/top of invoice, often near a logo
   - Look for: Company name near logo, "From:", "Payable to:", letterhead
   - Examples: "Forrester", "EY Outsourcing SAS", "Bioplex", "Positiva Compañía de Seguros", "Accenture", "Deloitte", "PwC", "KPMG", "Oracle", "SAP", "Microsoft", "IBM", "Salesforce", "Amazon Web Services", "Google Cloud"
   - IMPORTANT: Text near logos may have OCR errors. Common OCR error patterns:
     * Letter substitutions: "Positrva" → "Positiva", "lBM" → "IBM", "Orac1e" → "Oracle", "Microsof+" → "Microsoft"
     * Character misreads: "COMPANIA bE" → "COMPAÑÍA DE", "Accentrue" → "Accenture", "De1oitte" → "Deloitte"
     * Special characters: "PwC" as "Pw0" or "P//C", "&" as "8" or "S"
     * Spacing issues: "SalesForce" → "Salesforce", "Pay Pal" → "PayPal", "Face Book" → "Facebook"
     * Case confusion: "pWc" → "PwC", "ibm" → "IBM", "SAp" → "SAP"
   - Use context clues to infer correct company name:
     * Industry keywords nearby (e.g., "SEGUROS" → insurance company, "CONSULTING" → consulting firm)
     * Domain names in email/website (e.g., "@accenture.com" → "Accenture")
     * Tax ID numbers or registration numbers (often indicate official company name)
     * Address and phone number context (helps validate company identity)

4. invoice_date: The date the invoice was created/issued
   - Look for: "Invoice Date:", "Date:", "Dated:", near invoice number
   - CRITICAL: Return date in YYYY-MM-DD format (e.g., "2025-10-08", "2021-05-23", "2025-10-14")
   - Parse any format found (MM/DD/YYYY, DD.MM.YYYY, "October 14, 2025", etc.) and convert to YYYY-MM-DD

5. total_amount: The final total amount due
   - Look for: "Total:", "Amount Due:", "Grand Total:", "Total USD:", "TOTAL"
   - Usually bottom-right, in larger font
   - Include commas/decimals: "359,275.00", "6610.95", "17,458,973.14"
   - **DUAL-CURRENCY INVOICES**: Some invoices show amounts in MULTIPLE currencies (e.g., "Valor USD" AND "Valor COP" columns)
     * FIRST identify the invoice currency from "Moneda:", "Currency:", or currency field
     * THEN extract total_amount from the column matching that currency ONLY
     * Example: If Moneda: USD, extract from "Valor USD" column, NOT "Valor COP"
     * IGNORE amounts in other currencies - they are conversions, not the invoice amount

6. tax_amount: Tax/VAT amount
   - Look for: "Tax:", "VAT:", "Sales Tax:", "GST:", "IVA:"
   - Include formatting: "2,787,567.14", "596.45"
   - **DUAL-CURRENCY INVOICES**: Same rule as total_amount - extract from the column matching the invoice currency ONLY

7. currency: Currency CODE (NOT symbol!)
   - CRITICAL: Return ONLY 3-letter currency codes: USD, EUR, GBP, JPY, CAD, AUD, CHF, COP, CRC, MXN, BRL, etc.
   - NEVER return symbols like $, €, £, ¥
   - Look for currency codes or convert symbols: $ → USD, € → EUR, £ → GBP, ¥ → JPY
   - Usually near amounts or in header

8. purchase_order_number: Customer's PO/Reference number - CRITICAL FIELD
   
   **EXPECTED FORMAT:** PO-XXXXXX (e.g., "PO-123456", "PO-023027")
   - Always starts with "PO-" prefix
   - Followed by digits (typically 6 digits, but may vary)
   
   **WHERE TO LOOK:**
   - "PO:", "P.O.#:", "Purchase Order:", "PO Number:", "PO#", "P.O. Number:"
   - "Customer PO:", "Your Reference:", "Reference:", "Order No:"
   - May appear in header, near invoice number, or in a reference section
   - **ALSO CHECK LINE ITEM DESCRIPTIONS** - PO number may be embedded within line item text
     (e.g., "Consulting services per PO-123456", "Project ref: PO-789012 - Phase 1")
   
   **EXTRACTION RULES:**
   
   A. **Extract the identifier, normalize to PO-XXXXXX format:**
      - "PO-123456" → "PO-123456"
      - "PO#123456" → "PO-123456"
      - "PO 123456" → "PO-123456"
      - "P.O. 123456" → "PO-123456"
      - "123456" (when clearly labeled as PO) → "PO-123456"
      
   B. **Strip trailing text/descriptions:**
      - "PO-123456- test string" → "PO-123456"
      - "PO-123456 - Consulting Services" → "PO-123456"
      - "PO-123456 (Q1 Budget)" → "PO-123456"
      - "PO-123456 for software" → "PO-123456"
      
   C. **Clean trailing punctuation:**
      - "PO-123456-" → "PO-123456"
      - "PO-123456." → "PO-123456"
      - "PO-123456," → "PO-123456"
      - "PO-123456--" → "PO-123456"
      
   D. **Handle OCR errors in prefix:**
      - "P0-123456" (zero instead of O) → "PO-123456"
      - "PO-l23456" (lowercase L instead of 1) → "PO-123456"
      
   E. **Remove enclosing punctuation:**
      - "(PO-123456)" → "PO-123456"
      - "PO: (123456)" → "PO-123456"
   
   **DECISION LOGIC:**
   1. First check dedicated PO fields/labels in header or reference section
   2. If not found, scan line item descriptions for PO references
   3. Extract the numeric identifier
   4. Strip any trailing dash followed by text (descriptions/notes)
   5. Remove trailing punctuation (. , : -)
   6. Ensure result has "PO-" prefix + digits only
   7. Final format must be: PO-XXXXXX
   
   **EXAMPLES:**
   | Raw Text on Invoice                              | Correct Extraction |
   |--------------------------------------------------|-------------------|
   | "PO-123456- test string"                         | "PO-123456"       |
   | "PO-123456-"                                     | "PO-123456"       |
   | "PO-123456 (Annual Contract)"                    | "PO-123456"       |
   | "Purchase Order: 540473"                         | "PO-540473"       |
   | "PO#023027"                                      | "PO-023027"       |
   | "P.O. Number: 123456."                           | "PO-123456"       |
   | "P0-789012" (OCR error)                          | "PO-789012"       |
   | "(PO-123456)"                                    | "PO-123456"       |
   | Line item: "Consulting per PO-456789 - Q1"       | "PO-456789"       |
   | Line item: "Software license (ref: PO-111222)"  | "PO-111222"       |
   
   - Output format: Always "PO-" followed by the numeric identifier
   - If no PO number found, return empty string ""

9. memo_description: Return "Goods invoice" OR "Services invoice" OR "Goods and Services invoice"
    - Goods invoice = physical products, equipment, materials, supplies, inventory
    - Service invoice = labor, consulting, maintenance, subscriptions, software, professional services
    - Look at line items, descriptions, or invoice type indicators
    - If mixed, use predominant type. Default to "Service invoice" if unclear

EXTRACTION GUIDELINES:
- Use the most prominent/final value if multiple candidates exist
- For amounts in tables, use the final "Total" row, not line items
- Preserve original formatting for amounts (keep commas/decimals)
- For dates (invoice_date): ALWAYS normalize to YYYY-MM-DD format
- For currency: ALWAYS return 3-letter CODE (USD, EUR, etc.), NEVER symbols
- For memo_description: MUST be exactly "Goods invoice" or "Services invoice"
- For other text fields: Return exact text snippets, not interpreted values
- **OCR ERROR CORRECTION**: Some text may have OCR errors (misspellings). Use context to infer correct spelling:
  - Company names: "Positrva" → "Positiva", "COMPANIA bE" → "Compañía de", "Accentrue" → "Accenture", "lBM" → "IBM", "Orac1e" → "Oracle"
  - Common words: "lnvoice" → "Invoice", "Arnount" → "Amount", "Tota1" → "Total", "Datel" → "Date", "Nurnber" → "Number"
  - Numbers in text: "0" (zero) vs "O" (letter O), "1" (one) vs "l" (lowercase L) vs "I" (uppercase i)
  - Special characters: "&" as "8" or "S", "@" as "a" or "o", "ñ" as "n", "á/é/í/ó/ú" may lose accents
  - Use surrounding context (industry keywords, NIT numbers, addresses, domains) to validate correct spelling
- If field is not found or unclear, return empty string "" (except memo_description - always return one of the two options)

Invoice Text:
{invoice_text}

Respond with a JSON object containing all 9 fields."""

LINE_ITEMS_EXTRACT_PROMPT = """You are an expert at extracting line items from invoice text.

Extract ONLY TOP-LEVEL LINE ITEMS (main products/services being billed).

REQUIRED FIELDS FOR ALL LINE ITEMS:
1. description: Name of the product/service being billed
2. type: MUST be exactly "Goods" OR "Service" (case-sensitive)
3. amount: Total amount for this line item (e.g., "1500.00", "2500.00")

**CRITICAL - AMOUNT EXTRACTION (Context & Semantic Aware):**
The "amount" field should contain the MONETARY VALUE (dollars, euros, etc.) for this line item.

DISTINGUISHING AMOUNT vs QUANTITY:
- AMOUNT = Dollar/monetary value ($1,234.56, €500.00) 
- QUANTITY = Count of units ordered (1, 10, 3,000 units)
- "Order QTY", "Qty", "Quantity", "Units", "Count" columns = QUANTITY (not amount!)
- "Total", "Ext Price", "Extended", "Amount", "Price", "Cost" with $ = AMOUNT

HOW TO FIND AMOUNT:
1. Look for currency symbols ($, €, £, ¥) - that column is AMOUNT
2. Look for headers like "Total", "Amount", "Extended Price", "Net", "Subtotal per line"
3. If unit_price and quantity exist: amount = unit_price × quantity
4. If NO per-line monetary amount exists, set amount to "" (empty)

IMPORTANT - DO NOT USE QUANTITY AS AMOUNT:
- If "Order QTY" = 3,000 and no dollar column exists, amount should be "" NOT "3000"
- Pure counts without currency context are QUANTITY, not AMOUNT
- If there's only a SUBTOTAL at the bottom but no per-line amounts, leave amount empty

When in doubt:
- If value has $ or currency symbol → AMOUNT
- If column header says "Qty/Quantity/Units/Count" → QUANTITY (not amount!)
- If no clear monetary column exists → leave amount "" (empty)

ADDITIONAL FIELDS BASED ON TYPE:

**For GOODS (physical products):**
- unit_of_measure: EXTRACT the value from "Unit", "UOM", "Unidad", "Medida" column if present. Include ANY value found (e.g., "each", "unit", "box", "kg", "Sp", "Sv", "Un", "EA"). Do NOT leave empty if column value exists. Will be defaulted to "each" later if not found.
- quantity: Numeric quantity (e.g., "1", "10", "3.5") - return "" if not found
- unit_price: Price per unit (e.g., "150.00", "250.00") - return "" if not found
- service_start_date: "" (empty string - do not extract for Goods)
- service_end_date: "" (empty string - do not extract for Goods)

**For SERVICES (intangible services):**
- service_start_date: Start date of service period in YYYY-MM-DD format (e.g., "2024-01-01") - return "" if not found
- service_end_date: End date of service period in YYYY-MM-DD format (e.g., "2024-01-31") - return "" if not found
- **IMPORTANT**: If only ONE date is found for the service period, use that date for BOTH start and end dates
- unit_of_measure: "" (empty string - do not extract for Services)
- quantity: "" (empty string - do not extract for Services)
- unit_price: "" (empty string - do not extract for Services)

CLASSIFICATION GUIDELINES (for "type" field):
CRITICAL: The "type" field is REQUIRED and MUST be set to EITHER "Goods" OR "Service" for EVERY line item. NEVER leave it null or empty.

- **Goods**: Physical products that can be touched, shipped, or stored
  - Examples: computers, office supplies, food/beverages, clothing, furniture, equipment, materials, parts, inventory
  - Indicators: product names, model numbers, SKU, "units", physical quantities, material descriptions, brand names
  - Food/Beverage items (like "LANCHERA", "GASEOSA", "COCA COLA") are ALWAYS "Goods"
  
- **Service**: Intangible services, labor, or digital subscriptions
  - Examples: consulting, maintenance, support contracts, subscriptions, software licenses, professional services, training
  - Indicators: "consulting", "maintenance", "support", "subscription", "license", "professional services", date ranges
  
- If unclear, default to "Goods" if the item has quantity/unit_price, otherwise "Service"

REMEMBER: EVERY line item MUST have type set to "Goods" or "Service" - NEVER null!

EXTRACTION INSTRUCTIONS:
- First, determine if the line item is "Goods" or "Service"
- Then, extract ONLY the fields relevant to that type
- For Goods: extract unit_of_measure, quantity, unit_price (when visible); set service dates to "" (empty string)
- For Services: extract service_start_date, service_end_date (when visible); set unit fields to "" (empty string)
- Do NOT extract irrelevant fields - set them to "" (empty string)

CRITICAL DISTINCTION - Main Items vs Sub-Items:

**THE SEMANTIC TEST**: Ask yourself: "Does this row describe WHAT is being purchased, or HOW the price is calculated/adjusted?"

MAIN LINE ITEMS describe WHAT is being purchased (EXTRACT THESE):
- A product name, service name, or deliverable
- Something that could appear on a purchase order
- Has inherent value independent of other rows
- Examples: "Amazon S3", "Professional Consulting", "Dell Laptop XPS 15", "Cloud Hosting"

SUB-ITEMS describe HOW the price is adjusted (DO NOT EXTRACT):
- Price modifiers, adjustments, or calculations applied to a main item
- Would be meaningless without the parent item they modify
- Typically appear immediately after the item they adjust
- Negative amounts that reduce another item's price
- Aggregations like "Total", "Subtotal", "Net"
- Examples: Price adjustments, credits, refunds, volume pricing, promotional rates, fee breakdowns

**THE INDEPENDENCE TEST**: 
"If I removed all other rows, would this row still make sense as something being purchased?"
- YES → It's a main item (extract it)
- NO → It's a sub-item or summary (skip it)

**THE PURCHASE ORDER TEST**:
"Would this appear as a line on a purchase order?"
- YES → Extract it (e.g., "Cloud Storage Service", "Database Instance")
- NO → Skip it (e.g., "Enterprise Discount Applied", "Volume Pricing Adjustment")

ROWS TO ALWAYS SKIP:
- Rows that are adjustments TO something else (price modifiers)
- Rows with negative amounts that offset other rows (credits, discounts)
- Rows that only exist to explain pricing of another row
- Rows that aggregate or summarize other rows (subtotals, totals)
- Column headers, page headers, footers
- Banking details, payment instructions, notes

UNIVERSAL EXTRACTION RULES:
1. Look for line items tables with columns like "Description", "Quantity", "Unit Price", "Amount", "UOM", "Service Period"
2. Extract ONLY top-level rows (main products/services)
3. SKIP rows that are breakdowns/components of another item
4. SKIP subtotals, totals, tax summary rows, and headers
5. Preserve numeric formatting with decimals
6. ALWAYS classify each line item as "Goods" or "Service"
7. Extract ONLY fields relevant to the type - Goods get unit fields, Services get date fields
8. Set irrelevant or not found fields to "" (empty string)
9. Test: "Can this item be billed independently?" If no → skip it

**INTELLIGENT DATE EXTRACTION**:
- Service dates should be in YYYY-MM-DD format
- Parse ANY date format: MM/DD/YYYY, DD.MM.YYYY, YYYY/MM/DD, "Jan 1, 2024", "2025年10月31日" (Japanese), etc.
- MULTILINGUAL DATE LABELS - recognize ANY of these as potential service dates:
  * English: "Date", "From", "To", "Service Date", "Billing Date", "Period"
  * Japanese: "日付", "期間", "サービス日", "請求日", "開始日", "終了日"
  * Chinese: "日期", "期间", "服务日期", "开始日期", "结束日期"
  * Korean: "날짜", "기간", "서비스일", "시작일", "종료일"
  * Spanish: "Fecha", "Período", "Desde", "Hasta"
  * Portuguese: "Data", "Período", "De", "Até"
  * German: "Datum", "Zeitraum", "Von", "Bis", "Leistungsdatum"
  * French: "Date", "Période", "Du", "Au"
  * And other languages...
- CRITICAL: If a SERVICE line item has ANY date in its row, EXTRACT IT as the service date
- If only ONE date is found, use it for BOTH service_start_date and service_end_date
- Do NOT ignore dates just because the column is labeled generically (like "Date" or "日付")

**DUAL-CURRENCY INVOICES**:
- Extract amounts from the correct currency column only
- Ignore amounts in other currency columns

Return ONLY main line items in a JSON array.

FIELD REQUIREMENTS:
- All items: description, type, amount (always required, never empty)
- Goods items: unit_of_measure, quantity, unit_price (extract when available, "" if not found)
- Service items: service_start_date, service_end_date (extract when available, "" if not found)
- Set irrelevant or not found fields to "" (empty string)

CRITICAL VALIDATION:
- Every line item MUST have "type" set to either "Goods" or "Service"
- "type" can NEVER be empty or omitted
- Physical items (food, beverages, equipment, materials) = "Goods"
- Intangible services (consulting, subscriptions, licenses) = "Service"
- Only extract fields relevant to the type - set irrelevant fields to "" (empty string)

Invoice Text:
{invoice_text}

Respond with a JSON object: {{"line_items": [...]}}"""


LINE_ITEMS_CLASSIFICATION_PROMPT = """You are an expert invoice analyst specializing in extracting line items from diverse invoice formats worldwide.

{context_section}

=============================================================================
                           INVOICE DATA TO ANALYZE
=============================================================================
{table_text}

=============================================================================
                            EXTRACTION OBJECTIVE
=============================================================================
Extract ALL billable line items from the data above. Line items can appear in:
- Structured tables (bordered or borderless)
- Semi-structured lists
- Free-form text with amounts
- Multi-line descriptions

=============================================================================
                          LINE ITEM DEFINITION
=============================================================================
A LINE ITEM is a single billable product or service with:
- A description (what is being billed)
- An amount (price/cost)
- Optionally: quantity, unit price, dates, unit of measure

VALID LINE ITEMS INCLUDE:
- Product names with prices ("Office Chair - $299.00")
- Service descriptions ("Monthly Consulting - Jan 2025")
- Campaign/advertising codes ("ap-au-look-paidsocial-fb-evg | 3,775.96")
- License fees ("Software License Q1 2025")
- Subscription items ("Cloud Storage - 100GB - $9.99/mo")
- Equipment rentals ("Projector Rental - 3 days @ $50")
- Professional services ("Legal Review - 10 hrs @ $250/hr")

=============================================================================
                          NOT LINE ITEMS (SKIP)
=============================================================================
ALWAYS SKIP these - they are NOT billable line items:

TOTALS & SUBTOTALS:
- "Subtotal", "Total", "Grand Total", "Net Total", "Gross Total"
- "Balance Due", "Amount Due", "Total Due", "Sum"

TAXES & FEES:
- "Tax", "VAT", "GST", "IVA", "Sales Tax", "Service Tax"
- "Shipping", "Handling", "Freight", "Delivery Fee" (standalone)

HEADERS & METADATA:
- Column headers ("Description", "Amount", "Qty", "Price")
- Invoice metadata, page numbers, footer text

NON-BILLABLE ROWS:
- Banking information (IBAN, Account Numbers, SINPE)
- Contact information, addresses, payment instructions
- Notes, comments, disclaimers, empty rows

SUB-ITEMS (breakdowns of parent items - DO NOT EXTRACT):
- Usage details under a main service
- Fee components that sum to a parent item
- Indented child items explaining a parent
- Price adjustments, credits, discounts applied to a main item
- Rows that modify or reduce another item's price (negative amounts)
- Volume pricing adjustments, promotional rate modifications

**THE SEMANTIC TEST for is_line_item**: 
Ask: "Does this row describe WHAT is being purchased, or HOW the price is calculated/adjusted?"
- WHAT is being purchased → is_line_item: true
- HOW price is adjusted → is_line_item: false

**THE INDEPENDENCE TEST**:
"If I removed all other rows, would this row still make sense as something being purchased?"
- YES → is_line_item: true (e.g., "Amazon S3", "Database Hosting")
- NO → is_line_item: false (e.g., "Enterprise Discount", "Credit Applied")

**THE PURCHASE ORDER TEST**:
"Would this appear as a line on a purchase order?"
- YES → is_line_item: true
- NO → is_line_item: false

**THE VAGUE DESCRIPTION TEST**:
Descriptions that are too vague to identify WHAT is being purchased are NOT valid line items.
They are typically subtotals, aggregations, or breakdown components.

INVALID (too vague - just says "amounts" without specifying WHAT):
- "Charges" / "Frais" (charges for WHAT?)
- "Fees" / "Costs" / "Amounts" (fees for WHAT?)
- "Net Charges" / "Gross Charges" (subtotals, not items)
- "Total Charges" alone without context (aggregations)

VALID (specifies WHAT is being charged):
- "AWS Service Charges" (specifies AWS Services)
- "Professional Service Fees" (specifies Professional Services)
- "Cloud Hosting Charges" (specifies Cloud Hosting)
- "Consulting Fees" (specifies Consulting)

RULE: If the description is just a generic word like "Charges", "Fees", "Costs" 
without specifying the product/service, set is_line_item: false.

=============================================================================
                         CLASSIFICATION RULES
=============================================================================
Every line item MUST be classified as "Goods" OR "Service":

**GOODS** (Physical, tangible products):
- Equipment: computers, servers, monitors, printers
- Supplies: paper, ink, cleaning supplies, office supplies
- Materials: raw materials, construction materials, parts
- Food/Beverage: catering, refreshments, meals
- Furniture: desks, chairs, cabinets
- Inventory: products for resale, stock items
- INDICATORS: SKU, model numbers, "units", physical quantities, brand names

**SERVICES** (Intangible, labor, digital):
- Consulting: advisory, strategy, professional advice
- Advertising: campaigns, ads, media buying, social media
  * Campaign codes (ap-*, em-*, na-*, la-*) = Service
- Subscriptions: SaaS, cloud services, software licenses
- Professional: legal, accounting, design, engineering
- Maintenance: support contracts, repairs, upkeep
- Training: courses, workshops, certifications
- Hosting: cloud hosting, storage, bandwidth
- INDICATORS: date ranges, "consulting", "support", "license", hourly rates

CLASSIFICATION PRIORITY:
1. If description contains "campaign", "paidsocial", "advertising", "ad " → Service
2. If has quantity + unit price but no dates → likely Goods
3. If has service period/date range → Service
4. If physical/tangible item → Goods
5. If labor/work/digital → Service
6. When in doubt: Goods if countable, Service if time-based

=============================================================================
                         MULTI-LINE HANDLING
=============================================================================
DESCRIPTIONS MAY SPAN MULTIPLE LINES. Combine them intelligently:

Example: "Dell Latitude 5520 Laptop / Intel i7, 16GB RAM, 512GB SSD"
→ Combine as: "Dell Latitude 5520 Laptop - Intel i7, 16GB RAM, 512GB SSD"

RULES FOR MULTI-LINE:
- Combine description lines with " - " or ", " separator
- Extract dates from any line into the date fields
- Amount is usually on the last line or in a separate column

=============================================================================
                         AMOUNT & DATE EXTRACTION
=============================================================================
**CRITICAL - AMOUNT EXTRACTION (Context & Semantic Aware):**
The "amount" field should contain the MONETARY VALUE (dollars, euros, etc.) for this line item.

DISTINGUISHING AMOUNT vs QUANTITY:
- AMOUNT = Dollar/monetary value ($1,234.56, €500.00)
- QUANTITY = Count of units ordered (1, 10, 3,000 units)
- "Order QTY", "Qty", "Quantity", "Units", "Count" columns = QUANTITY (not amount!)
- "Total", "Ext Price", "Extended", "Amount", "Price", "Cost" with $ = AMOUNT

HOW TO FIND AMOUNT:
1. Look for currency symbols ($, €, £, ¥) - that column is AMOUNT
2. Look for headers like "Total", "Amount", "Extended Price", "Net", "Subtotal per line"
3. If unit_price and quantity exist: amount = unit_price × quantity
4. If NO per-line monetary amount exists, set amount to "" (empty)

IMPORTANT - DO NOT USE QUANTITY AS AMOUNT:
- If "Order QTY" = 3,000 and no dollar column exists, amount should be "" NOT "3000"
- Pure counts without currency context are QUANTITY, not AMOUNT
- If there's only a SUBTOTAL at the bottom but no per-line amounts, leave amount empty

When in doubt:
- If value has $ or currency symbol → AMOUNT
- If column header says "Qty/Quantity/Units/Count" → QUANTITY (not amount!)
- If no clear monetary column exists → leave amount "" (empty)

AMOUNTS - Formatting:
- Preserve formatting: "1,234.56", "1.234,56"
- Handle currency symbols: $, €, £, ¥, COP, USD, EUR
- For dual-currency: use the primary invoice currency
- Negative amounts: preserve sign ("-500.00" for credits)

DATES (for Services only):
- Parse ANY format and convert to YYYY-MM-DD
- "01/15/2025" → "2025-01-15"
- "15.01.2025" → "2025-01-15"  
- "January 15, 2025" → "2025-01-15"
- "Sep-25" → "2025-09-01"
- Look for: "From/To", "Start/End", "Period", "Service Date", "Billing Period"

=============================================================================
                        EXTRACTION OUTPUT
=============================================================================
For each line item, provide:
- row_index: 0-based index (first data row = 0)
- is_line_item: true if valid billable item, false otherwise
- description: Full description (combined if multi-line)
- type: "Goods" or "Service" (REQUIRED, never empty)
- amount: Total amount as string ("1,234.56")
- quantity: Number of units (Goods only, "" for Service)
- unit_price: Price per unit (Goods only, "" for Service)
- unit_of_measure: EXTRACT the value from "Unit", "UOM", "Unidad", "Medida" column if present. Include ANY value found (e.g., "each", "unit", "box", "kg", "Sp", "Sv", "Un", "EA"). Do NOT leave empty if column value exists.
- service_start_date: YYYY-MM-DD (Service only, "" for Goods)
- service_end_date: YYYY-MM-DD (Service only, "" for Goods)
- If only ONE date is found for a service, use it for BOTH service_start_date and service_end_date

=============================================================================
                         CRITICAL REMINDERS
=============================================================================
- Extract EVERY row that has a description + amount
- ALWAYS set type to "Goods" or "Service" (never null/empty)
- Campaign codes (ap-*, em-*, na-*, la-*) are SERVICES (advertising)
- Skip subtotals, totals, taxes, headers, empty rows
- Combine multi-line descriptions intelligently
- Set unused fields to empty string ""
- Be consistent with previous page context if provided
- When in doubt, include the item (prefer false positives over misses)
- For services with only one date, duplicate it for both start and end

Return ALL valid line items from the data above."""

# Unified prompt that works for both bordered tables and freeform text
# Uses {invoice_data} instead of {table_text} for flexibility
LINE_ITEMS_UNIFIED_PROMPT = """You are an expert invoice analyst specializing in extracting line items from diverse invoice formats worldwide.

{context_section}

=============================================================================
                           INVOICE DATA TO ANALYZE
=============================================================================
{invoice_data}

=============================================================================
                            EXTRACTION OBJECTIVE
=============================================================================
Extract ALL billable line items from the data above. Line items can appear in:
- Structured tables (bordered or borderless)
- Semi-structured lists
- Free-form text with amounts
- Multi-line descriptions

=============================================================================
                          LINE ITEM DEFINITION
=============================================================================
A LINE ITEM is a single billable product or service with:
- A description (what is being billed)
- An amount (price/cost)
- Optionally: quantity, unit price, dates, unit of measure

VALID LINE ITEMS INCLUDE:
- Product names with prices ("Office Chair - $299.00")
- Service descriptions ("Monthly Consulting - Jan 2025")
- Campaign/advertising codes ("ap-au-look-paidsocial-fb-evg | 3,775.96")
- License fees ("Software License Q1 2025")
- Subscription items ("Cloud Storage - 100GB - $9.99/mo")
- Equipment rentals ("Projector Rental - 3 days @ $50")
- Professional services ("Legal Review - 10 hrs @ $250/hr")

=============================================================================
                          NOT LINE ITEMS (SKIP)
=============================================================================
ALWAYS SKIP these - they are NOT billable line items:

TOTALS & SUBTOTALS:
- "Subtotal", "Total", "Grand Total", "Net Total", "Gross Total"
- "Balance Due", "Amount Due", "Total Due", "Sum"

TAXES & FEES (when standalone summary rows):
- "Tax", "VAT", "GST", "IVA", "Sales Tax", "Service Tax"
- "Shipping", "Handling", "Freight", "Delivery Fee" (standalone)

HEADERS & METADATA:
- Column headers ("Description", "Amount", "Qty", "Price")
- Invoice metadata, page numbers, footer text

NON-BILLABLE ROWS:
- Banking information (IBAN, Account Numbers, SINPE)
- Contact information, addresses, payment instructions
- Notes, comments, disclaimers, empty rows

SUB-ITEMS (breakdowns of parent items - DO NOT EXTRACT):
- Usage details under a main service
- Fee components that sum to a parent item
- Indented child items explaining a parent
- Price adjustments, credits, discounts applied to a main item
- Rows that modify or reduce another item's price (negative amounts)
- Volume pricing adjustments, promotional rate modifications

**THE SEMANTIC TEST for is_line_item**: 
Ask: "Does this row describe WHAT is being purchased, or HOW the price is calculated/adjusted?"
- WHAT is being purchased → is_line_item: true
- HOW price is adjusted → is_line_item: false

**THE INDEPENDENCE TEST**:
"If I removed all other rows, would this row still make sense as something being purchased?"
- YES → is_line_item: true (e.g., "Amazon S3", "Database Hosting")
- NO → is_line_item: false (e.g., "Enterprise Discount", "Credit Applied")

**THE PURCHASE ORDER TEST**:
"Would this appear as a line on a purchase order?"
- YES → is_line_item: true
- NO → is_line_item: false

**THE VAGUE DESCRIPTION TEST**:
Descriptions that are too vague to identify WHAT is being purchased are NOT valid line items.
They are typically subtotals, aggregations, or breakdown components.

INVALID (too vague - just says "amounts" without specifying WHAT):
- "Charges" / "Frais" (charges for WHAT?)
- "Fees" / "Costs" / "Amounts" (fees for WHAT?)
- "Net Charges" / "Gross Charges" (subtotals, not items)
- "Total Charges" alone without context (aggregations)

VALID (specifies WHAT is being charged):
- "AWS Service Charges" (specifies AWS Services)
- "Professional Service Fees" (specifies Professional Services)
- "Cloud Hosting Charges" (specifies Cloud Hosting)
- "Consulting Fees" (specifies Consulting)

RULE: If the description is just a generic word like "Charges", "Fees", "Costs" 
without specifying the product/service, set is_line_item: false.

=============================================================================
                         CLASSIFICATION RULES
=============================================================================
Every line item MUST be classified as "Goods" OR "Service":

**GOODS** (Physical, tangible products):
- Equipment: computers, servers, monitors, printers
- Supplies: paper, ink, cleaning supplies, office supplies
- Materials: raw materials, construction materials, parts
- Food/Beverage: catering, refreshments, meals
- Furniture: desks, chairs, cabinets
- Inventory: products for resale, stock items
- INDICATORS: SKU, model numbers, "units", physical quantities, brand names

**SERVICES** (Intangible, labor, digital):
- Consulting: advisory, strategy, professional advice
- Advertising: campaigns, ads, media buying, social media
  * Campaign codes (ap-*, em-*, na-*, la-*) = Service
- Subscriptions: SaaS, cloud services, software licenses
- Professional: legal, accounting, design, engineering
- Maintenance: support contracts, repairs, upkeep
- Training: courses, workshops, certifications
- Hosting: cloud hosting, storage, bandwidth
- INDICATORS: date ranges, "consulting", "support", "license", hourly rates

CLASSIFICATION PRIORITY:
1. If description contains "campaign", "paidsocial", "advertising", "ad " → Service
2. If has quantity + unit price but no dates → likely Goods
3. If has service period/date range → Service
4. If physical/tangible item → Goods
5. If labor/work/digital → Service
6. When in doubt: Goods if countable, Service if time-based

=============================================================================
                         MULTI-LINE HANDLING
=============================================================================
DESCRIPTIONS MAY SPAN MULTIPLE LINES. Combine them intelligently:

Example: "Dell Latitude 5520 Laptop / Intel i7, 16GB RAM, 512GB SSD"
→ Combine as: "Dell Latitude 5520 Laptop - Intel i7, 16GB RAM, 512GB SSD"

RULES FOR MULTI-LINE:
- Combine description lines with " - " or ", " separator
- Extract dates from any line into the date fields
- Amount is usually on the last line or in a separate column

=============================================================================
                         AMOUNT & DATE EXTRACTION
=============================================================================
**CRITICAL - AMOUNT EXTRACTION (Context & Semantic Aware):**
The "amount" field should contain the MONETARY VALUE (dollars, euros, etc.) for this line item.

DISTINGUISHING AMOUNT vs QUANTITY:
- AMOUNT = Dollar/monetary value ($1,234.56, €500.00)
- QUANTITY = Count of units ordered (1, 10, 3,000 units)
- "Order QTY", "Qty", "Quantity", "Units", "Count" columns = QUANTITY (not amount!)
- "Total", "Ext Price", "Extended", "Amount", "Price", "Cost" with $ = AMOUNT

**CRITICAL - TOTAL vs SUBTOTAL PRIORITY:**
When a table has BOTH "Subtotal" AND "Total" columns:
- ALWAYS use the "Total" column for the amount field
- "Total" = final amount INCLUDING taxes, fees, adjustments
- "Subtotal" = intermediate amount BEFORE taxes/fees
- If only "Subtotal" exists (no "Total" column), use Subtotal
- Examples of Total columns: "Total", "Total CAD", "Total USD", "Grand Total", "Net Total"
- Examples of Subtotal columns: "Subtotal", "Sub-total", "Pre-tax Amount"

**CRITICAL - ROW-TO-AMOUNT ALIGNMENT:**
Each line item's amount MUST come from the SAME ROW as its description.
- DO NOT shift amounts between rows
- If a row's Total column is $0.00 or empty, that row's amount IS $0.00 or empty
- Never "borrow" an amount from an adjacent row
- Match description and amount by their visual horizontal alignment

**CRITICAL - MULTI-VALUE TABLES (Category Summary Tables):**
When text is extracted from a table with multiple columns like:
  Category | Discount | Subtotal | GST | HST | PST | QST | Total
  
The text appears as sequential lines where each category is followed by ITS OWN values:
  CATEGORY_A          <-- Category name
  $discount_A         <-- Discount for CATEGORY_A  
  $subtotal_A         <-- Subtotal for CATEGORY_A
  $gst_A              <-- GST for CATEGORY_A
  $hst_A              <-- HST for CATEGORY_A
  $pst_A              <-- PST for CATEGORY_A
  $qst_A              <-- QST for CATEGORY_A
  $total_A            <-- TOTAL for CATEGORY_A (USE THIS!)
  CATEGORY_B          <-- Next category
  $discount_B         <-- Discount for CATEGORY_B
  ...

**CRITICAL RULE**: The values between CATEGORY_A and CATEGORY_B belong to CATEGORY_A.
- For CATEGORY_A, use $total_A (the LAST value BEFORE CATEGORY_B appears)
- For CATEGORY_B, use $total_B (the LAST value BEFORE CATEGORY_C appears)
- DO NOT assign CATEGORY_B's values to CATEGORY_A!

Example:
  OTHERS → $16,742.68 → $0.00 → $0.00 → $0.00 → $0.00 → $0.00 → $0.00 → REGISTRATION...
  OTHERS' amount = $0.00 (the value just BEFORE "REGISTRATION")
  
  REGISTRATION → $8,824.40 → $25,424.40 → $0.00 → $3,305.17 → $0.00 → $0.00 → $28,729.57 → BOOTH EQUIPMENT...
  REGISTRATION's amount = $28,729.57 (the value just BEFORE "BOOTH EQUIPMENT")

HOW TO FIND AMOUNT:
1. Look for currency symbols ($, €, £, ¥) - that column is AMOUNT
2. **PREFER "Total" column over "Subtotal" column when both exist**
3. Look for headers like "Total", "Amount", "Extended Price", "Net"
4. If unit_price and quantity exist: amount = unit_price × quantity
5. If NO per-line monetary amount exists, set amount to "" (empty)

IMPORTANT - DO NOT USE QUANTITY AS AMOUNT:
- If "Order QTY" = 3,000 and no dollar column exists, amount should be "" NOT "3000"
- Pure counts without currency context are QUANTITY, not AMOUNT
- If there's only a SUBTOTAL at the bottom but no per-line amounts, leave amount empty

When in doubt:
- If value has $ or currency symbol → AMOUNT
- If column header says "Qty/Quantity/Units/Count" → QUANTITY (not amount!)
- If no clear monetary column exists → leave amount "" (empty)

AMOUNTS - Formatting:
- Preserve formatting: "1,234.56", "1.234,56"
- Handle currency symbols: $, €, £, ¥, COP, USD, EUR
- For dual-currency: use the primary invoice currency
- Negative amounts: preserve sign ("-500.00" for credits)

**INTELLIGENT DATE EXTRACTION FOR LINE ITEMS:**

Look for ANY date column or field associated with each line item row. Dates in invoices often represent when services were performed or goods delivered.

MULTILINGUAL DATE COLUMN LABELS (recognize these as potential service dates):
- English: "Date", "From", "To", "Start", "End", "Period", "Service Date", "Billing Date", "Transaction Date", "Delivery Date"
- Japanese: "日付" (Date), "期間" (Period), "サービス日" (Service Date), "請求日" (Billing Date), "納品日" (Delivery Date), "開始日" (Start Date), "終了日" (End Date)
- Chinese: "日期" (Date), "期间" (Period), "服务日期" (Service Date), "开始日期" (Start Date), "结束日期" (End Date), "交付日期" (Delivery Date)
- Korean: "날짜" (Date), "기간" (Period), "서비스일" (Service Date), "시작일" (Start Date), "종료일" (End Date)
- Spanish: "Fecha" (Date), "Período" (Period), "Desde" (From), "Hasta" (To), "Fecha de Servicio", "Fecha de Entrega"
- Portuguese: "Data" (Date), "Período" (Period), "De" (From), "Até" (To), "Data do Serviço", "Data de Entrega"
- French: "Date", "Période", "Du" (From), "Au" (To), "Date de Service", "Date de Livraison"
- German: "Datum" (Date), "Zeitraum" (Period), "Von" (From), "Bis" (To), "Leistungsdatum" (Service Date), "Lieferdatum"
- Italian: "Data", "Periodo", "Da" (From), "A" (To), "Data del Servizio", "Data di Consegna"
- Dutch: "Datum" (Date), "Periode" (Period), "Van" (From), "Tot" (To), "Servicedatum", "Leveringsdatum"
- Swedish: "Datum" (Date), "Period", "Från" (From), "Till" (To), "Tjänstedatum" (Service Date)
- Norwegian: "Dato" (Date), "Periode" (Period), "Fra" (From), "Til" (To), "Tjeneste dato"
- Hebrew: "תאריך" (Date), "תקופה" (Period), "מ" (From), "עד" (To)
- Arabic: "تاريخ" (Date), "فترة" (Period), "من" (From), "إلى" (To)
- Russian: "Дата" (Date), "Период" (Period), "С" (From), "По" (To)
- Polish: "Data" (Date), "Okres" (Period), "Od" (From), "Do" (To)
- Indonesian: "Tanggal" (Date), "Periode" (Period), "Dari" (From), "Sampai" (To)

DATE EXTRACTION DECISION LOGIC:
1. If a date appears in the SAME ROW as a line item, it likely represents when that service/good was delivered
2. For SERVICES (cleaning, consulting, subscription, etc.):
   - ANY date in that row represents when the service was performed
   - Use that date for BOTH service_start_date AND service_end_date (unless separate start/end dates exist)
3. For recurring services (daily, weekly, monthly):
   - A single date often means "services through this date" or "services for this billing period"
4. If explicit start AND end dates exist separately, use them as-is
5. If only a transaction/billing date exists, use it for BOTH dates

DATE FORMATS (parse ANY format and convert to YYYY-MM-DD):
- "01/15/2025" → "2025-01-15"
- "15.01.2025" → "2025-01-15"
- "2025/10/31" → "2025-10-31"
- "January 15, 2025" → "2025-01-15"
- "15 Jan 2025" → "2025-01-15"
- "Sep-25" → "2025-09-01"
- "2025年10月31日" (Japanese) → "2025-10-31"
- "2025年10月31号" (Chinese) → "2025-10-31"

CRITICAL: Do NOT ignore dates just because they appear in a generic "Date" column. If a SERVICE line item has a date in its row, EXTRACT IT as the service date.

=============================================================================
                        EXTRACTION OUTPUT
=============================================================================
For each line item, provide:
- row_index: 0-based index from table (use -1 if extracting from free-form text without row numbers)
- is_line_item: true if valid billable item, false otherwise
- description: Full description (combined if multi-line)
- type: "Goods" or "Service" (REQUIRED, never empty)
- amount: Total amount as string ("1,234.56"), "" if not available
- quantity: Number of units - EXTRACT IF CLEARLY VISIBLE in the data, regardless of type
- unit_price: Price per unit - EXTRACT IF CLEARLY VISIBLE in the data, regardless of type
- unit_of_measure: EXTRACT the value from "Unit", "UOM", "Unidad", "Medida" column if present. Include ANY value found (e.g., "each", "Users Per Month", "box", "kg", "Sp", "Sv", "Un", "EA"). Do NOT leave empty if column value exists.
- service_start_date: YYYY-MM-DD - EXTRACT IF CLEARLY VISIBLE, regardless of type
- service_end_date: YYYY-MM-DD - EXTRACT IF CLEARLY VISIBLE, regardless of type

**IMPORTANT**: Extract ALL fields that are CLEARLY VISIBLE in the data, regardless of whether the item is classified as Goods or Service. For example:
- A SaaS subscription (Service) may have quantity="13,000" and unit_of_measure="Users Per Month" - EXTRACT THEM
- A product (Goods) may have service dates if it's a subscription - EXTRACT THEM
- If only ONE date is found for a service, use it for BOTH service_start_date and service_end_date
- Only leave fields empty ("") if the data is NOT present

=============================================================================
                         CRITICAL REMINDERS
=============================================================================
- Extract EVERY row that has a description + amount
- ALWAYS set type to "Goods" or "Service" (never null/empty)
- Campaign codes (ap-*, em-*, na-*, la-*) are SERVICES (advertising)
- Skip subtotals, totals, taxes, headers, empty rows
- Combine multi-line descriptions intelligently
- Set unused fields to empty string ""
- Be consistent with previous page context if provided
- When in doubt, include the item (prefer false positives over misses)
- For services with only one date, duplicate it for both start and end

Return ALL valid line items from the data above."""
