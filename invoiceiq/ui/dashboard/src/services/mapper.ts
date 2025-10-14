// Mapper to convert backend API responses to frontend Invoice objects

import { InvoiceResponse } from './api';
import { Invoice } from '../components/InvoiceCard';
import { getViewPdfUrl } from './api';

/**
 * Parse amount from string to number
 */
function parseAmount(amount: string | null): number {
  if (!amount) return 0;
  
  // Remove currency symbols and commas
  const cleaned = amount.replace(/[$,]/g, '');
  const parsed = parseFloat(cleaned);
  
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Format date string to readable format
 */
function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A';
  
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

/**
 * Map backend InvoiceResponse to frontend Invoice
 */
export function mapInvoiceResponse(response: InvoiceResponse): Invoice {
  return {
    id: response.ticket_number,
    invoiceNumber: response.invoice_number || 'N/A',
    liftTicketNumber: response.ticket_number,
    purchaseOrderNumber: response.purchase_order_number || 'N/A',
    status: response.status,
    reason: undefined, // Backend doesn't provide reason yet
    amount: parseAmount(response.total_amount),
    vendor: response.vendor_name || 'Unknown Vendor',
    date: formatDate(response.invoice_date || response.created_at),
    pdfUrl: getViewPdfUrl(response.ticket_number),
    createdAt: response.created_at,
    updatedAt: response.updated_at,
    emailFrom: response.email_from || undefined,
  };
}

/**
 * Map array of backend responses to frontend Invoices
 */
export function mapInvoiceResponses(responses: InvoiceResponse[]): Invoice[] {
  return responses.map(mapInvoiceResponse);
}

