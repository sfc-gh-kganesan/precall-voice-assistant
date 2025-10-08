import { useState, useMemo } from "react";
import { InvoiceStatistics } from "./components/InvoiceStatistics";
import { InvoiceFilters } from "./components/InvoiceFilters";
import { GroupedInvoiceView } from "./components/GroupedInvoiceView";
import { PDFViewer } from "./components/PDFViewer";
import { BulkActionsBar } from "./components/BulkActionsBar";
import { Invoice } from "./components/InvoiceCard";
import { mockInvoices } from "./data/mockInvoices";
import { toast } from "sonner@2.0.3";
import { Toaster } from "./components/ui/sonner";

export default function App() {
  const [invoices, setInvoices] = useState<Invoice[]>(mockInvoices);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<Set<string>>(new Set());
  const [groupBy, setGroupBy] = useState<string>("none");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // Filter invoices based on search term
  const filteredInvoices = useMemo(() => {
    if (!searchTerm) return invoices;
    
    const term = searchTerm.toLowerCase();
    return invoices.filter(invoice =>
      invoice.invoiceNumber.toLowerCase().includes(term) ||
      invoice.liftTicketNumber.toLowerCase().includes(term) ||
      invoice.purchaseOrderNumber.toLowerCase().includes(term) ||
      invoice.vendor.toLowerCase().includes(term)
    );
  }, [searchTerm, invoices]);

  // Calculate statistics
  const approvedCount = filteredInvoices.filter(inv => inv.status === 'approved').length;
  const pendingCount = filteredInvoices.filter(inv => inv.status === 'pending').length;
  const rejectedCount = filteredInvoices.filter(inv => inv.status === 'rejected').length;

  const handleViewPdf = (invoice: Invoice) => {
    setSelectedInvoice(invoice);
  };

  const handleClosePdf = () => {
    setSelectedInvoice(null);
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setGroupBy("none");
  };

  const handleUpdateInvoiceStatus = (invoiceId: string, newStatus: Invoice['status'], reason?: string) => {
    setInvoices(prev => prev.map(invoice => 
      invoice.id === invoiceId 
        ? { ...invoice, status: newStatus, reason: newStatus === 'approved' ? undefined : reason }
        : invoice
    ));
    
    // Remove from selected invoices
    setSelectedInvoiceIds(prev => {
      const newSet = new Set(prev);
      newSet.delete(invoiceId);
      return newSet;
    });

    toast.success(`Invoice ${invoiceId} moved to ${newStatus}`);
  };

  const handleBulkStatusUpdate = (invoiceIds: string[], newStatus: Invoice['status']) => {
    const count = invoiceIds.length;
    setInvoices(prev => prev.map(invoice => 
      invoiceIds.includes(invoice.id) 
        ? { ...invoice, status: newStatus, reason: newStatus === 'approved' ? undefined : invoice.reason }
        : invoice
    ));
    
    // Clear selection
    setSelectedInvoiceIds(new Set());
    
    toast.success(`${count} invoice${count !== 1 ? 's' : ''} moved to ${newStatus}`);
  };

  const handleSelectInvoice = (invoiceId: string, selected: boolean) => {
    setSelectedInvoiceIds(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(invoiceId);
      } else {
        newSet.delete(invoiceId);
      }
      return newSet;
    });
  };

  const handleSelectAll = (invoiceIds: string[]) => {
    setSelectedInvoiceIds(new Set(invoiceIds));
  };

  const handleClearSelection = () => {
    setSelectedInvoiceIds(new Set());
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto p-6">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex items-center justify-center">
              <img 
                src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Snowflake_Logo.svg/1280px-Snowflake_Logo.svg.png" 
                alt="Snowflake Logo" 
                className="h-12 w-auto object-contain"
              />
            </div>
            <div>
              <h1 className="mb-1 bg-gradient-to-r from-[var(--snowflake-blue)] to-[var(--snowflake-teal)] bg-clip-text text-transparent">InvoiceIQ Dashboard</h1>
              <p className="text-muted-foreground">
                AI-powered invoice processing and validation system
              </p>
            </div>
          </div>
        </div>

        {/* Statistics */}
        <InvoiceStatistics
          totalInvoices={filteredInvoices.length}
          approvedCount={approvedCount}
          pendingCount={pendingCount}
          rejectedCount={rejectedCount}
        />

        {/* Bulk Actions */}
        {selectedInvoiceIds.size > 0 && (
          <BulkActionsBar
            selectedCount={selectedInvoiceIds.size}
            onBulkAction={handleBulkStatusUpdate}
            selectedInvoiceIds={Array.from(selectedInvoiceIds)}
            onClearSelection={handleClearSelection}
          />
        )}

        {/* Filters */}
        <InvoiceFilters
          groupBy={groupBy}
          onGroupByChange={setGroupBy}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          onClearFilters={handleClearFilters}
        />

        {/* Invoice Columns */}
        <GroupedInvoiceView
          invoices={filteredInvoices}
          groupBy={groupBy}
          onViewPdf={handleViewPdf}
          selectedInvoiceIds={selectedInvoiceIds}
          onSelectInvoice={handleSelectInvoice}
          onSelectAll={handleSelectAll}
          onClearSelection={handleClearSelection}
        />

        {/* PDF Viewer */}
        <PDFViewer
          invoice={selectedInvoice}
          isOpen={selectedInvoice !== null}
          onClose={handleClosePdf}
          onUpdateStatus={handleUpdateInvoiceStatus}
        />
      </div>
      
      {/* Toast notifications */}
      <Toaster />
    </div>
  );
}