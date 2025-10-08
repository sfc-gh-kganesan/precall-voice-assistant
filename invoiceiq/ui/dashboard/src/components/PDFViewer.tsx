import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Download, X, CheckCircle, Clock, XCircle } from "lucide-react";
import { Invoice } from "./InvoiceCard";
import { useState } from "react";

interface PDFViewerProps {
  invoice: Invoice | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdateStatus: (invoiceId: string, status: Invoice['status'], reason?: string) => void;
}

export function PDFViewer({ invoice, isOpen, onClose, onUpdateStatus }: PDFViewerProps) {
  const [selectedStatus, setSelectedStatus] = useState<Invoice['status'] | ''>('');
  
  if (!invoice) return null;

  const handleDownload = () => {
    // In a real app, this would trigger a download of the PDF
    const link = document.createElement('a');
    link.href = invoice.pdfUrl;
    link.download = `invoice-${invoice.invoiceNumber}.pdf`;
    link.click();
  };

  const handleStatusUpdate = () => {
    if (selectedStatus && selectedStatus !== invoice.status) {
      onUpdateStatus(invoice.id, selectedStatus);
      setSelectedStatus('');
      onClose();
    }
  };

  const getStatusIcon = (status: Invoice['status']) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      case 'rejected':
        return <XCircle className="w-4 h-4 text-red-600" />;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] p-0">
        <DialogHeader className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle>Invoice {invoice.invoiceNumber}</DialogTitle>
              <DialogDescription>
                View and manage invoice status for {invoice.vendor}
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-36">
                  <SelectValue placeholder="Change status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="approved" className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-green-600" />
                    Approved
                  </SelectItem>
                  <SelectItem value="pending" className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-yellow-600" />
                    Pending
                  </SelectItem>
                  <SelectItem value="rejected" className="flex items-center gap-2">
                    <XCircle className="w-4 h-4 text-red-600" />
                    Rejected
                  </SelectItem>
                </SelectContent>
              </Select>
              {selectedStatus && selectedStatus !== invoice.status && (
                <Button 
                  size="sm" 
                  onClick={handleStatusUpdate}
                  className="bg-[var(--snowflake-blue)] hover:bg-[var(--snowflake-blue)]/90"
                >
                  Update
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" />
                Download
              </Button>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>
        
        <div className="flex-1 p-4">
          <div className="w-full h-[600px] border rounded-lg overflow-hidden">
            {/* PDF Viewer - Using iframe as fallback, in production you'd use a proper PDF viewer */}
            <iframe
              src={invoice.pdfUrl}
              className="w-full h-full"
              title={`Invoice ${invoice.invoiceNumber}`}
            />
          </div>
          
          <div className="mt-4 p-4 bg-muted rounded-lg">
            <h4 className="mb-2">Invoice Details</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Lift Ticket #:</span> {invoice.liftTicketNumber}
              </div>
              <div>
                <span className="text-muted-foreground">Purchase Order #:</span> {invoice.purchaseOrderNumber}
              </div>
              <div>
                <span className="text-muted-foreground">Vendor:</span> {invoice.vendor}
              </div>
              <div>
                <span className="text-muted-foreground">Amount:</span> ${invoice.amount.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}