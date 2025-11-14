// Type definitions for InvoiceIQ API

export interface InvoiceResponse {
    [key: string]: unknown;
    id: string;
    ticket_number: string;
    status: "approved" | "pending" | "rejected";
    relative_path: string | null;
    file_url: string;
    // Invoice fields
    vendor_name: string | null;
    invoice_number: string | null;
    invoice_date: string | null;
    total_amount: string | null;
    purchase_order_number: string | null;
    due_date: string | null;
    banking_details: string | null;
    freight_shipping_amount: string | null;
    invoice_currency: string | null;
    memo_description: string | null;
    payment_terms: string | null;
    payment_type: string | null;
    prepaid_flag: boolean | null;
    quantity: string | null;
    service_end_date: string | null;
    service_start_date: string | null;
    shipped_to_address: string | null;
    snowflake_entity: string | null;
    snowflake_tax_id: string | null;
    tax_amount: string | null;
    unit_price: string | null;
    vendor_address: string | null;
    vendor_tax_id: string | null;
    // AI fields
    ai_reasoning: string | null;
    ai_processed_at: string | null;
    // Edit tracking
    last_edited_by: string | null;
    last_edited_at: string | null;
    // Metadata
    submission_id: string | null;
    created_at: string;
    updated_at: string;
    email_from: string | null;
    email_subject: string | null;
    // Bounding boxes
    bounding_boxes: Array<{
        bbox: { x0: number; x1: number; y0: number; y1: number };
        page: number;
        text: string;
        type: string;
    }> | null;
    fields_with_bounding_boxes: Record<
        string,
        {
            bbox: { x0: number; x1: number; y0: number; y1: number };
            confidence: number;
            page: number;
            value: string;
        }
    > | null;
}

export interface InvoiceListResponse {
    success: boolean;
    invoices: InvoiceResponse[];
    total_count: number;
    limit: number;
    offset: number;
}

export interface InvoiceStatsResponse {
    success: boolean;
    approved: number;
    pending: number;
    rejected: number;
    total: number;
}

export interface InvoicesByStatusResponse {
    success: boolean;
    approved: InvoiceResponse[];
    pending: InvoiceResponse[];
    rejected: InvoiceResponse[];
    approved_count: number;
    pending_count: number;
    rejected_count: number;
}

export interface UpdateStatusRequest {
    ticket_numbers: string[];
    status: "approved" | "pending" | "rejected";
}

export interface UpdateStatusResponse {
    success: boolean;
    updated_count: number;
    message: string;
}

export interface UpdateFieldsResponse {
    success: boolean;
    message: string;
}

export interface ReprocessInvoiceResponse {
    success: boolean;
    message: string;
    invoice_id: string;
}

export interface GenerateEmailRequest {
    ai_reasoning: string;
    vendor_name?: string | null;
    invoice_number?: string | null;
}

export interface GenerateEmailResponse {
    success: boolean;
    email_template: string;
}
