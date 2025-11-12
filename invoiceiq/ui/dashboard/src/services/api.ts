// API service for InvoiceIQ backend
// This file now re-exports from the new react-query hooks and types
// Kept for backward compatibility

// Re-export types
export type {
    InvoiceResponse,
    InvoiceListResponse,
    InvoiceStatsResponse,
    InvoicesByStatusResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
    UpdateFieldsResponse,
    ReprocessInvoiceResponse,
} from "./types";

// Re-export utility functions
export { getViewPdfUrl, getDownloadPdfUrl, downloadPdf } from "./hooks";

// For backward compatibility, export legacy functions that use the hooks internally
// These should be migrated to use the hooks directly in components
import {
    InvoicesByStatusResponse,
    InvoiceListResponse,
    UpdateStatusResponse,
    UpdateFieldsResponse,
    ReprocessInvoiceResponse,
} from "./types";

const API_BASE_URL = "/api";

/**
 * @deprecated Use useAllInvoices hook instead
 */
export async function fetchAllInvoices(
    limit: number = 100,
): Promise<InvoicesByStatusResponse> {
    const params = new URLSearchParams({
        limit: limit.toString(),
    });

    const url = `${API_BASE_URL}/invoices/all?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

/**
 * @deprecated Use useSearchInvoices hook instead
 */
export async function searchInvoices(
    searchBy: "liftTicket" | "purchaseOrder",
    searchTerm: string,
    limit: number = 1000,
    offset: number = 0,
): Promise<InvoiceListResponse> {
    const params = new URLSearchParams({
        search_by: searchBy,
        search_term: searchTerm,
        limit: limit.toString(),
        offset: offset.toString(),
    });

    const url = `${API_BASE_URL}/invoices/search?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`,
        );
    }

    return response.json();
}

/**
 * @deprecated Use useUpdateInvoiceStatus hook instead
 */
export async function updateInvoiceStatus(
    ticketNumbers: string[],
    status: "approved" | "pending" | "rejected",
): Promise<UpdateStatusResponse> {
    const url = `${API_BASE_URL}/invoices/status`;

    const requestBody = {
        ticket_numbers: ticketNumbers,
        status: status,
    };

    const response = await fetch(url, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`,
        );
    }

    return response.json();
}

/**
 * @deprecated Use useUpdateInvoiceFields hook instead
 */
export async function updateInvoiceFields(
    ticketNumber: string,
    fields: Record<string, unknown>,
): Promise<UpdateFieldsResponse> {
    const url = `${API_BASE_URL}/invoices/${ticketNumber}/fields`;

    const response = await fetch(url, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(fields),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`,
        );
    }

    return response.json();
}

/**
 * @deprecated Use useReprocessInvoice hook instead
 */
export async function reprocessInvoice(
    ticketNumber: string,
): Promise<ReprocessInvoiceResponse> {
    const url = `${API_BASE_URL}/invoices/${ticketNumber}/reprocess`;

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`,
        );
    }

    return response.json();
}
