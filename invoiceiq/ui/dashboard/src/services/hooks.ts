// React Query hooks for InvoiceIQ API
import {
    useMutation,
    useQuery,
    useQueryClient,
    UseQueryOptions,
    UseMutationOptions,
} from "react-query";
import type {
    InvoiceListResponse,
    InvoiceStatsResponse,
    InvoicesByStatusResponse,
    UpdateStatusResponse,
    UpdateFieldsResponse,
    ReprocessInvoiceResponse,
    UpdateStatusRequest,
} from "./types";

// Use /api prefix to route through our Express proxy server
const API_BASE_URL = "/api";

// Query Keys
export const queryKeys = {
    invoiceStats: ["invoiceStats"] as const,
    allInvoices: (limit?: number) => ["allInvoices", limit] as const,
    invoices: (status?: string, limit?: number, offset?: number) =>
        ["invoices", status, limit, offset] as const,
    searchInvoices: (
        searchBy: string,
        searchTerm: string,
        limit?: number,
        offset?: number,
    ) => ["searchInvoices", searchBy, searchTerm, limit, offset] as const,
};

// API Functions
async function fetchInvoiceStatsApi(): Promise<InvoiceStatsResponse> {
    const url = `${API_BASE_URL}/invoices/stats`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

async function fetchAllInvoicesApi(
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

async function fetchInvoicesApi(
    status?: string,
    limit: number = 100,
    offset: number = 0,
): Promise<InvoiceListResponse> {
    const params = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
    });

    if (status) {
        params.append("status", status);
    }

    const url = `${API_BASE_URL}/invoices?${params.toString()}`;
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
}

async function searchInvoicesApi(
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

async function updateInvoiceStatusApi(
    ticketNumbers: string[],
    status: "approved" | "pending" | "rejected",
): Promise<UpdateStatusResponse> {
    const url = `${API_BASE_URL}/invoices/status`;

    const requestBody: UpdateStatusRequest = {
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

async function updateInvoiceFieldsApi(
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

async function reprocessInvoiceApi(
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

// Query Hooks
export function useInvoiceStats(
    options?: Omit<
        UseQueryOptions<InvoiceStatsResponse, Error>,
        "queryKey" | "queryFn"
    >,
) {
    return useQuery<InvoiceStatsResponse, Error>(
        queryKeys.invoiceStats,
        fetchInvoiceStatsApi,
        options,
    );
}

export function useAllInvoices(
    limit: number = 100,
    options?: Omit<
        UseQueryOptions<InvoicesByStatusResponse, Error>,
        "queryKey" | "queryFn"
    >,
) {
    return useQuery<InvoicesByStatusResponse, Error>(
        queryKeys.allInvoices(limit),
        () => fetchAllInvoicesApi(limit),
        options,
    );
}

export function useInvoices(
    status?: string,
    limit: number = 100,
    offset: number = 0,
    options?: Omit<
        UseQueryOptions<InvoiceListResponse, Error>,
        "queryKey" | "queryFn"
    >,
) {
    return useQuery<InvoiceListResponse, Error>(
        queryKeys.invoices(status, limit, offset),
        () => fetchInvoicesApi(status, limit, offset),
        options,
    );
}

export function useSearchInvoices(
    searchBy: "liftTicket" | "purchaseOrder",
    searchTerm: string,
    limit: number = 1000,
    offset: number = 0,
    options?: Omit<
        UseQueryOptions<InvoiceListResponse, Error>,
        "queryKey" | "queryFn"
    >,
) {
    return useQuery<InvoiceListResponse, Error>(
        queryKeys.searchInvoices(searchBy, searchTerm, limit, offset),
        () => searchInvoicesApi(searchBy, searchTerm, limit, offset),
        {
            ...options,
            enabled: Boolean(searchTerm.trim()) && (options?.enabled ?? true),
        },
    );
}

// Mutation Hooks
interface UpdateStatusVariables {
    ticketNumbers: string[];
    status: "approved" | "pending" | "rejected";
}

export function useUpdateInvoiceStatus(
    options?: UseMutationOptions<
        UpdateStatusResponse,
        Error,
        UpdateStatusVariables
    >,
) {
    const queryClient = useQueryClient();

    return useMutation<UpdateStatusResponse, Error, UpdateStatusVariables>(
        ({ ticketNumbers, status }) =>
            updateInvoiceStatusApi(ticketNumbers, status),
        {
            ...options,
            onSuccess: (data, variables, context) => {
                // Invalidate and refetch related queries
                queryClient.invalidateQueries(queryKeys.invoiceStats);
                queryClient.invalidateQueries(queryKeys.allInvoices());
                queryClient.invalidateQueries(queryKeys.invoices());

                if (options?.onSuccess) {
                    options.onSuccess(data, variables, context);
                }
            },
        },
    );
}

interface UpdateFieldsVariables {
    ticketNumber: string;
    fields: Record<string, unknown>;
}

export function useUpdateInvoiceFields(
    options?: UseMutationOptions<
        UpdateFieldsResponse,
        Error,
        UpdateFieldsVariables
    >,
) {
    const queryClient = useQueryClient();

    return useMutation<UpdateFieldsResponse, Error, UpdateFieldsVariables>(
        ({ ticketNumber, fields }) =>
            updateInvoiceFieldsApi(ticketNumber, fields),
        {
            ...options,
            onSuccess: (data, variables, context) => {
                // Invalidate and refetch related queries
                queryClient.invalidateQueries(queryKeys.allInvoices());
                queryClient.invalidateQueries(queryKeys.invoices());

                if (options?.onSuccess) {
                    options.onSuccess(data, variables, context);
                }
            },
        },
    );
}

interface ReprocessInvoiceVariables {
    ticketNumber: string;
}

export function useReprocessInvoice(
    options?: UseMutationOptions<
        ReprocessInvoiceResponse,
        Error,
        ReprocessInvoiceVariables
    >,
) {
    const queryClient = useQueryClient();

    return useMutation<
        ReprocessInvoiceResponse,
        Error,
        ReprocessInvoiceVariables
    >(({ ticketNumber }) => reprocessInvoiceApi(ticketNumber), {
        ...options,
        onSuccess: (data, variables, context) => {
            // Invalidate and refetch related queries
            queryClient.invalidateQueries(queryKeys.allInvoices());
            queryClient.invalidateQueries(queryKeys.invoices());

            if (options?.onSuccess) {
                options.onSuccess(data, variables, context);
            }
        },
    });
}

// Utility Functions (non-query related)
export function getViewPdfUrl(ticketNumber: string): string {
    return `${API_BASE_URL}/invoices/${ticketNumber}/view`;
}

export function getDownloadPdfUrl(ticketNumber: string): string {
    return `${API_BASE_URL}/invoices/${ticketNumber}/download`;
}

export async function downloadPdf(ticketNumber: string): Promise<void> {
    const url = getDownloadPdfUrl(ticketNumber);

    try {
        // Create a temporary anchor element to trigger download
        const a = document.createElement("a");
        a.href = url;
        a.download = `${ticketNumber}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    } catch (error) {
        console.error("Error downloading PDF:", error);
        throw error;
    }
}
