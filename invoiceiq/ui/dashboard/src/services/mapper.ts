// Mapper to convert backend API responses to frontend Invoice objects

import { Invoice } from "../components/InvoiceCard";
import { InvoiceResponse } from "./api";
import { getViewPdfUrl } from "./api";

/**
 * Parse amount from string to number
 */
function parseAmount(amount: string | null): number {
    if (!amount) return 0;

    // Remove currency symbols and commas
    const cleaned = amount.replace(/[$,]/g, "");
    const parsed = parseFloat(cleaned);

    return isNaN(parsed) ? 0 : parsed;
}

/**
 * Format date string to readable format
 */
function formatDate(dateStr: string | null): string {
    if (!dateStr) return "N/A";

    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    } catch {
        return dateStr;
    }
}

/**
 * Map backend InvoiceResponse to frontend Invoice
 */
export function mapInvoiceResponse(response: InvoiceResponse): Invoice {
    const totalAmount = parseAmount(response.total_amount);
    const vendorName = response.vendor_name || "Unknown Vendor";
    const ticketNumber = response.ticket_number;
    const invoiceDate = response.invoice_date || undefined;

    return {
        id: ticketNumber,
        invoiceNumber: response.invoice_number || "N/A",
        liftTicketNumber: ticketNumber,
        ticketNumber: ticketNumber, // Alias
        purchaseOrderNumber: response.purchase_order_number || "N/A",
        status: response.status,
        reason: undefined, // Backend doesn't provide reason yet
        amount: totalAmount,
        totalAmount: totalAmount, // Alias
        vendor: vendorName,
        vendorName: vendorName, // Alias
        date: formatDate(response.invoice_date || response.created_at),
        invoiceDate: invoiceDate,
        pdfUrl: getViewPdfUrl(ticketNumber),
        createdAt: response.created_at,
        updatedAt: response.updated_at,
        emailFrom: response.email_from || undefined,
        // Additional invoice fields
        dueDate: response.due_date || undefined,
        bankingDetails: response.banking_details || undefined,
        freightShippingAmount: response.freight_shipping_amount
            ? parseAmount(response.freight_shipping_amount)
            : undefined,
        invoiceCurrency: response.invoice_currency || undefined,
        memoDescription: response.memo_description || undefined,
        paymentTerms: response.payment_terms || undefined,
        paymentType: response.payment_type || undefined,
        prepaidFlag: response.prepaid_flag || undefined,
        quantity: response.quantity || undefined,
        serviceEndDate: response.service_end_date || undefined,
        serviceStartDate: response.service_start_date || undefined,
        shippedToAddress: response.shipped_to_address || undefined,
        snowflakeEntity: response.snowflake_entity || undefined,
        snowflakeTaxId: response.snowflake_tax_id || undefined,
        taxAmount: response.tax_amount
            ? parseAmount(response.tax_amount)
            : undefined,
        unitPrice: response.unit_price
            ? parseAmount(response.unit_price)
            : undefined,
        vendorAddress: response.vendor_address || undefined,
        vendorTaxId: response.vendor_tax_id || undefined,
        // AI fields
        aiReasoning: response.ai_reasoning || undefined,
        aiProcessedAt: response.ai_processed_at || undefined,
        // Edit tracking
        lastEditedBy: response.last_edited_by || undefined,
        lastEditedAt: response.last_edited_at || undefined,
        // Metadata
        submissionId: response.submission_id || undefined,
        emailSubject: response.email_subject || undefined,
    };
}

/**
 * Map array of backend responses to frontend Invoices
 */
export function mapInvoiceResponses(responses: InvoiceResponse[]): Invoice[] {
    return responses.map(mapInvoiceResponse);
}
