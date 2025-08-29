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
    invoiceNumber: 'IN-094386',
    vendorName: 'EOS IT MANAGEMENT SOLUTIONS INC',
    amount: 80860.62,
    exceptionType: 'MISMATCH',
    dateReceived: '2025-08-27',
    priority: 'HIGH',
    assignedTo: 'Seth Li',
    pdfUrl: 'https://drive.google.com/file/d/1Z0cu1kHU37GXKjhyNoj8dt7ziIK_nDpE/view?usp=sharing',
  },
  {
    id: '2',
    invoiceNumber: 'INV-094505',
    vendorName: 'Amazon Web Services, Inc.',
    amount: 232496.40,
    exceptionType: 'MISMATCH',
    dateReceived: '2025-08-27',
    priority: 'MEDIUM',
    pdfUrl: 'https://drive.google.com/file/d/1zzjGLDE8hca9v8KAHh99bgNBr69BkX1P/view?usp=sharing',
  },
  {
    id: '3',
    invoiceNumber: 'IN-095314',
    vendorName: 'Blue Cloud',
    amount: 140000,
    exceptionType: 'DUPLICATE',
    dateReceived: '2025-08-26',
    priority: 'LOW',
    assignedTo: 'Sarah Johnson',
    pdfUrl: 'https://drive.google.com/file/d/1p_8elcJkmYeSePvtBQ5aOaOS0sIT2h9m/view?usp=sharing',
  },
  {
    id: '4',
    invoiceNumber: 'IN-095603',
    vendorName: 'Crowe',
    amount: 375.00,
    exceptionType: 'MISSING_PO',
    dateReceived: '2025-08-26',
    priority: 'HIGH',
    pdfUrl: 'https://drive.google.com/file/d/1_3Td04fODENG6qK9piB_xMkH_144vg95/view?usp=sharing',
  },
  {
    id: '5',
    invoiceNumber: 'IN-095663',
    vendorName: 'Digital China Technology Limited',
    amount: 289513.33,
    exceptionType: 'MISMATCH',
    dateReceived: '2025-08-25',
    priority: 'MEDIUM',
    assignedTo: 'Mike Davis',
    pdfUrl: 'https://drive.google.com/file/d/16uXWJSsq2DgPN0pySr9hcG3GmubdyvG8/view?usp=sharing',
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
