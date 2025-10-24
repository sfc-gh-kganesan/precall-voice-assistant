import { AlertCircle, CheckCircle, Clock, Eye } from 'lucide-react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader } from './ui/card';
import { Checkbox } from './ui/checkbox';

export interface Invoice {
  id: string;
  invoiceNumber: string;
  liftTicketNumber: string;
  ticketNumber: string; // Alias for liftTicketNumber
  purchaseOrderNumber: string;
  status: 'approved' | 'pending' | 'rejected';
  reason?: string;
  amount: number;
  totalAmount: number; // Alias for amount
  vendor: string;
  vendorName: string; // Alias for vendor
  date: string;
  invoiceDate?: string; // Original invoice date
  pdfUrl: string;
  createdAt?: string;
  updatedAt?: string;
  emailFrom?: string;
  // Additional invoice fields
  dueDate?: string;
  bankingDetails?: string;
  freightShippingAmount?: number;
  invoiceCurrency?: string;
  memoDescription?: string;
  paymentTerms?: string;
  paymentType?: string;
  prepaidFlag?: boolean;
  quantity?: string;
  serviceEndDate?: string;
  serviceStartDate?: string;
  shippedToAddress?: string;
  snowflakeEntity?: string;
  snowflakeTaxId?: string;
  taxAmount?: number;
  unitPrice?: number;
  vendorAddress?: string;
  vendorTaxId?: string;
  // AI fields
  aiReasoning?: string;
  aiProcessedAt?: string;
  // Edit tracking
  lastEditedBy?: string;
  lastEditedAt?: string;
  // Metadata
  submissionId?: string;
  emailSubject?: string;
}

interface InvoiceCardProps {
  invoice: Invoice;
  onViewPdf: (invoice: Invoice) => void;
  isSelected?: boolean;
  onSelect?: (invoiceId: string, selected: boolean) => void;
  showSelection?: boolean;
}

export function InvoiceCard({
  invoice,
  onViewPdf,
  isSelected = false,
  onSelect,
  showSelection = false,
}: InvoiceCardProps) {
  const getStatusIcon = () => {
    switch (invoice.status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case 'rejected':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
    }
  };

  const getStatusColor = () => {
    switch (invoice.status) {
      case 'approved':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'pending':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'rejected':
        return 'bg-rose-100 text-rose-800 border-rose-200';
    }
  };

  return (
    <Card
      className={`hover:shadow-md transition-all duration-200 border-l-4 ${
        invoice.status === 'approved'
          ? 'border-l-emerald-500'
          : invoice.status === 'pending'
            ? 'border-l-amber-500'
            : 'border-l-rose-500'
      } ${isSelected ? 'ring-2 ring-[var(--snowflake-blue)] shadow-lg' : ''}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {showSelection && (
              <Checkbox
                checked={isSelected}
                onCheckedChange={(checked) => onSelect?.(invoice.id, !!checked)}
                className="data-[state=checked]:bg-[var(--snowflake-blue)] data-[state=checked]:border-[var(--snowflake-blue)]"
              />
            )}
            <div className="flex items-center gap-2">
              {getStatusIcon()}
              <Badge className={`${getStatusColor()} rounded-full`}>
                {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
              </Badge>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewPdf(invoice)}
            className="flex items-center gap-1 hover:bg-[var(--snowflake-light-blue)] hover:border-[var(--snowflake-blue)]"
          >
            <Eye className="w-3 h-3" />
            View
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div>
            <p className="text-sm">
              <span className="text-muted-foreground">Invoice #:</span> {invoice.invoiceNumber}
            </p>
            <p className="text-sm">
              <span className="text-muted-foreground">Lift Ticket #:</span>{' '}
              {invoice.liftTicketNumber}
            </p>
            <p className="text-sm">
              <span className="text-muted-foreground">PO #:</span> {invoice.purchaseOrderNumber}
            </p>
          </div>

          <div className="pt-2 border-t">
            <p className="text-sm">
              <span className="text-muted-foreground">Vendor:</span> {invoice.vendor}
            </p>
            <p className="text-sm">
              <span className="text-muted-foreground">Amount:</span> $
              {invoice.amount.toLocaleString()}
            </p>
            <p className="text-sm text-muted-foreground">{invoice.date}</p>
          </div>

          {invoice.reason && (
            <div className="pt-2 border-t">
              <p className="text-sm">
                <span className="text-muted-foreground">Reason:</span>
              </p>
              <p className="text-sm bg-gradient-to-r from-[var(--snowflake-light-blue)] to-blue-50 p-3 rounded-lg mt-1 border border-[var(--snowflake-blue)]/20">
                {invoice.reason}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
