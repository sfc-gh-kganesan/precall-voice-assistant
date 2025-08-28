export interface InvoiceException {
  id: string;
  invoiceNumber: string;
  vendorName: string;
  amount: number;
  exceptionType: 'MISMATCH' | 'MISSING_PO' | 'DUPLICATE' | 'INSUFFICIENT_FUNDS';
  dateReceived: string;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  assignedTo?: string;
}

export interface InvoiceMetrics {
  totalInvoices: number;
  autoProcessedPercentage: number;
  pendingExceptions: number;
  averageProcessingTime: number;
  processed: {
    autoProcessed: number;
    manuallyReviewed: number;
    rejected: number;
  };
}

export interface ActionItem {
  id: string;
  title: string;
  description: string;
  type: 'UPLOAD' | 'REVIEW' | 'ASSIGN' | 'REPORT';
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  dueDate?: string;
}