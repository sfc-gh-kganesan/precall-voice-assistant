import type { InvoiceException, InvoiceMetrics, ActionItem } from '../types';

export const mockMetrics: InvoiceMetrics = {
  totalInvoices: 2847,
  autoProcessedPercentage: 78,
  pendingExceptions: 34,
  averageProcessingTime: 2.4,
  processed: {
    autoProcessed: 2221,
    manuallyReviewed: 456,
    rejected: 170,
  },
};

export const mockExceptions: InvoiceException[] = [
  {
    id: '1',
    invoiceNumber: 'INV-2024-001234',
    vendorName: 'Acme Corp',
    amount: 15750.00,
    exceptionType: 'MISSING_PO',
    dateReceived: '2024-08-27',
    priority: 'HIGH',
    assignedTo: 'John Smith',
  },
  {
    id: '2',
    invoiceNumber: 'INV-2024-001235',
    vendorName: 'Tech Solutions Inc',
    amount: 3240.50,
    exceptionType: 'MISMATCH',
    dateReceived: '2024-08-27',
    priority: 'MEDIUM',
  },
  {
    id: '3',
    invoiceNumber: 'INV-2024-001236',
    vendorName: 'Office Supplies Ltd',
    amount: 892.75,
    exceptionType: 'DUPLICATE',
    dateReceived: '2024-08-26',
    priority: 'LOW',
    assignedTo: 'Sarah Johnson',
  },
  {
    id: '4',
    invoiceNumber: 'INV-2024-001237',
    vendorName: 'Professional Services Co',
    amount: 28500.00,
    exceptionType: 'INSUFFICIENT_FUNDS',
    dateReceived: '2024-08-26',
    priority: 'HIGH',
  },
  {
    id: '5',
    invoiceNumber: 'INV-2024-001238',
    vendorName: 'Marketing Agency',
    amount: 5670.25,
    exceptionType: 'MISMATCH',
    dateReceived: '2024-08-25',
    priority: 'MEDIUM',
    assignedTo: 'Mike Davis',
  },
];

export const mockActionItems: ActionItem[] = [
  {
    id: '1',
    title: 'Review High Priority Exceptions',
    description: '4 high priority exceptions requiring immediate attention',
    type: 'REVIEW',
    priority: 'HIGH',
    dueDate: '2024-08-28',
  },
  {
    id: '2',
    title: 'Upload Pending Invoices',
    description: '12 invoices waiting to be uploaded from email inbox',
    type: 'UPLOAD',
    priority: 'MEDIUM',
  },
  {
    id: '3',
    title: 'Assign Unassigned Exceptions',
    description: '8 exceptions need to be assigned to team members',
    type: 'ASSIGN',
    priority: 'MEDIUM',
  },
  {
    id: '4',
    title: 'Generate Weekly Report',
    description: 'Weekly processing summary due for management',
    type: 'REPORT',
    priority: 'LOW',
    dueDate: '2024-08-30',
  },
];