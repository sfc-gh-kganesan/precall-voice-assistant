// API service for InvoiceIQ backend

// Use /api prefix to route through our Express proxy server
// The proxy server handles internal SPCS communication to the backend
const API_BASE_URL = '/api';

export interface InvoiceResponse {
  id: string;
  ticket_number: string;
  status: 'approved' | 'pending' | 'rejected';
  relative_path: string | null;
  vendor_name: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  total_amount: string | null;
  purchase_order_number: string | null;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  email_from: string | null;
  email_subject: string | null;
  file_url: string;
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

