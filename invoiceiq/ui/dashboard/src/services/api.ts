// API service for InvoiceIQ backend

// Use /api prefix to route through our Express proxy server
// The proxy server handles internal SPCS communication to the backend
const API_BASE_URL = '/api';

export interface InvoiceResponse {
  id: string;
  ticket_number: string;
  status: 'approved' | 'pending' | 'rejected';
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
}

export interface InvoiceListResponse {
  success: boolean;
  invoices: InvoiceResponse[];
  total_count: number;
  limit: number;
  offset: number;
}

/**
 * Fetch invoices from the backend
 * @param status Filter by status (approved, pending, rejected)
 * @param limit Number of invoices to fetch
 * @param offset Pagination offset
 */
export async function fetchInvoices(
  status?: string,
  limit: number = 100,
  offset: number = 0
): Promise<InvoiceListResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (status) {
    params.append('status', status);
  }

  const url = `${API_BASE_URL}/invoices?${params.toString()}`;

  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching invoices:', error);
    throw error;
  }
}

/**
 * Search invoices by Lift Ticket # or Purchase Order #
 * @param searchBy Field to search: 'liftTicket' or 'purchaseOrder'
 * @param searchTerm Search term (exact match, case-insensitive)
 * @param limit Number of invoices to fetch
 * @param offset Pagination offset
 */
export async function searchInvoices(
  searchBy: 'liftTicket' | 'purchaseOrder',
  searchTerm: string,
  limit: number = 1000,
  offset: number = 0
): Promise<InvoiceListResponse> {
  const params = new URLSearchParams({
    search_by: searchBy,
    search_term: searchTerm,
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const url = `${API_BASE_URL}/invoices/search?${params.toString()}`;

  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error searching invoices:', error);
    throw error;
  }
}

/**
 * Get the URL for viewing a PDF inline
 */
export function getViewPdfUrl(ticketNumber: string): string {
  return `${API_BASE_URL}/invoices/${ticketNumber}/view`;
}

/**
 * Get the URL for downloading a PDF
 */
export function getDownloadPdfUrl(ticketNumber: string): string {
  return `${API_BASE_URL}/invoices/${ticketNumber}/download`;
}

/**
 * Download a PDF file
 */
export async function downloadPdf(ticketNumber: string): Promise<void> {
  const url = getDownloadPdfUrl(ticketNumber);
  
  try {
    // Create a temporary anchor element to trigger download
    const a = document.createElement('a');
    a.href = url;
    a.download = `${ticketNumber}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  } catch (error) {
    console.error('Error downloading PDF:', error);
    throw error;
  }
}

export interface UpdateStatusRequest {
  ticket_numbers: string[];
  status: 'approved' | 'pending' | 'rejected';
}

export interface UpdateStatusResponse {
  success: boolean;
  updated_count: number;
  message: string;
}

/**
 * Update the status of one or more invoices
 * @param ticketNumbers Array of ticket numbers to update
 * @param status New status (approved, pending, rejected)
 */
export async function updateInvoiceStatus(
  ticketNumbers: string[],
  status: 'approved' | 'pending' | 'rejected'
): Promise<UpdateStatusResponse> {
  const url = `${API_BASE_URL}/invoices/status`;
  
  const requestBody: UpdateStatusRequest = {
    ticket_numbers: ticketNumbers,
    status: status,
  };

  try {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data: UpdateStatusResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error updating invoice status:', error);
    throw error;
  }
}

export interface UpdateFieldsResponse {
  success: boolean;
  message: string;
}

/**
 * Update invoice fields
 * @param ticketNumber Ticket number of the invoice to update
 * @param fields Object containing the fields to update
 */
export async function updateInvoiceFields(
  ticketNumber: string,
  fields: Record<string, any>
): Promise<UpdateFieldsResponse> {
  const url = `${API_BASE_URL}/invoices/${ticketNumber}/fields`;
  
  try {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(fields),
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data: UpdateFieldsResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error updating invoice fields:', error);
    throw error;
  }
}

export interface ReprocessInvoiceResponse {
  success: boolean;
  message: string;
  invoice_id: string;
}

/**
 * Trigger agent to reprocess an invoice after user edits
 * @param ticketNumber Ticket number of the invoice to reprocess
 */
export async function reprocessInvoice(
  ticketNumber: string
): Promise<ReprocessInvoiceResponse> {
  const url = `${API_BASE_URL}/invoices/${ticketNumber}/reprocess`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    
    const data: ReprocessInvoiceResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error reprocessing invoice:', error);
    throw error;
  }
}

