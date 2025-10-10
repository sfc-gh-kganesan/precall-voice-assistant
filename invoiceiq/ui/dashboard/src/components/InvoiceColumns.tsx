import React, { useState, useEffect } from "react";
import { InvoiceCard, Invoice } from "./InvoiceCard";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Checkbox } from "./ui/checkbox";
import { Loader2, AlertCircle } from "lucide-react";
import { fetchInvoices } from "../services/api";
import { mapInvoiceResponses } from "../services/mapper";
import { Alert, AlertDescription } from "./ui/alert";

interface InvoiceColumnsProps {
  onViewPdf: (invoice: Invoice) => void;
  selectedInvoiceIds: Set<string>;
  onSelectInvoice: (invoiceId: string, selected: boolean) => void;
  onSelectAll: (invoiceIds: string[]) => void;
  onClearSelection: () => void;
  refreshTrigger?: number; // Optional prop to trigger refresh
}

export function InvoiceColumns({ 
  onViewPdf, 
  selectedInvoiceIds, 
  onSelectInvoice, 
  onSelectAll, 
  onClearSelection,
  refreshTrigger = 0
}: InvoiceColumnsProps) {
  const [approvedInvoices, setApprovedInvoices] = useState<Invoice[]>([]);
  const [pendingInvoices, setPendingInvoices] = useState<Invoice[]>([]);
  const [rejectedInvoices, setRejectedInvoices] = useState<Invoice[]>([]);
  
  const [loadingApproved, setLoadingApproved] = useState(true);
  const [loadingPending, setLoadingPending] = useState(true);
  const [loadingRejected, setLoadingRejected] = useState(true);
  
  const [errorApproved, setErrorApproved] = useState<string | null>(null);
  const [errorPending, setErrorPending] = useState<string | null>(null);
  const [errorRejected, setErrorRejected] = useState<string | null>(null);

  // Fetch approved invoices
  useEffect(() => {
    let isMounted = true;
    
    async function loadApprovedInvoices() {
      try {
        setLoadingApproved(true);
        setErrorApproved(null);
        const response = await fetchInvoices('approved', 100, 0);
        if (isMounted) {
          setApprovedInvoices(mapInvoiceResponses(response.invoices));
        }
      } catch (error) {
        if (isMounted) {
          setErrorApproved(error instanceof Error ? error.message : 'Failed to load approved invoices');
        }
      } finally {
        if (isMounted) {
          setLoadingApproved(false);
        }
      }
    }
    
    loadApprovedInvoices();
    return () => { isMounted = false; };
  }, [refreshTrigger]);

  // Fetch pending invoices
  useEffect(() => {
    let isMounted = true;
    
    async function loadPendingInvoices() {
      try {
        setLoadingPending(true);
        setErrorPending(null);
        const response = await fetchInvoices('pending', 100, 0);
        if (isMounted) {
          setPendingInvoices(mapInvoiceResponses(response.invoices));
        }
      } catch (error) {
        if (isMounted) {
          setErrorPending(error instanceof Error ? error.message : 'Failed to load pending invoices');
        }
      } finally {
        if (isMounted) {
          setLoadingPending(false);
        }
      }
    }
    
    loadPendingInvoices();
    return () => { isMounted = false; };
  }, [refreshTrigger]);

  // Fetch rejected invoices
  useEffect(() => {
    let isMounted = true;
    
    async function loadRejectedInvoices() {
      try {
        setLoadingRejected(true);
        setErrorRejected(null);
        const response = await fetchInvoices('rejected', 100, 0);
        if (isMounted) {
          setRejectedInvoices(mapInvoiceResponses(response.invoices));
        }
      } catch (error) {
        if (isMounted) {
          setErrorRejected(error instanceof Error ? error.message : 'Failed to load rejected invoices');
        }
      } finally {
        if (isMounted) {
          setLoadingRejected(false);
        }
      }
    }
    
    loadRejectedInvoices();
    return () => { isMounted = false; };
  }, [refreshTrigger]);

  const getColumnInvoiceIds = (columnInvoices: Invoice[]) => 
    columnInvoices.map(inv => inv.id);

  const getSelectedCountInColumn = (columnInvoices: Invoice[]) =>
    columnInvoices.filter(inv => selectedInvoiceIds.has(inv.id)).length;

  const isAllSelectedInColumn = (columnInvoices: Invoice[]) =>
    columnInvoices.length > 0 && getSelectedCountInColumn(columnInvoices) === columnInvoices.length;

  const handleSelectAllInColumn = (columnInvoices: Invoice[]) => {
    const columnIds = getColumnInvoiceIds(columnInvoices);
    if (isAllSelectedInColumn(columnInvoices)) {
      // Deselect all in this column
      columnIds.forEach(id => onSelectInvoice(id, false));
    } else {
      // Select all in this column
      onSelectAll(columnIds);
    }
  };

  const ColumnHeader = ({ 
    title, 
    count, 
    color, 
    columnInvoices 
  }: { 
    title: string; 
    count: number; 
    color: string; 
    columnInvoices: Invoice[];
  }) => {
    const selectedCount = getSelectedCountInColumn(columnInvoices);
    const allSelected = isAllSelectedInColumn(columnInvoices);
    const someSelected = selectedCount > 0 && selectedCount < columnInvoices.length;

    return (
      <CardHeader className="pb-4 bg-gradient-to-r from-[var(--snowflake-light-blue)]/30 to-transparent">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {columnInvoices.length > 0 && (
                <Checkbox
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onCheckedChange={() => handleSelectAllInColumn(columnInvoices)}
                  className="data-[state=checked]:bg-[var(--snowflake-blue)] data-[state=checked]:border-[var(--snowflake-blue)]"
                />
              )}
              {title}
            </div>
            <Badge variant="secondary" className={`${color} rounded-full`}>
              {count}
            </Badge>
            {selectedCount > 0 && (
              <Badge className="bg-[var(--snowflake-blue)] text-white rounded-full">
                {selectedCount} selected
              </Badge>
            )}
          </CardTitle>
        </div>
      </CardHeader>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Approved Column */}
      <Card className="border-t-4 border-t-emerald-500 shadow-sm">
        <ColumnHeader 
          title="Approved" 
          count={approvedInvoices.length} 
          color="bg-emerald-100 text-emerald-800"
          columnInvoices={approvedInvoices}
        />
        <CardContent>
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {loadingApproved ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading...</span>
              </div>
            ) : errorApproved ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorApproved}</AlertDescription>
              </Alert>
            ) : approvedInvoices.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No approved invoices</p>
            ) : (
              approvedInvoices.map(invoice => (
                <InvoiceCard
                  key={invoice.id}
                  invoice={invoice}
                  onViewPdf={onViewPdf}
                  isSelected={selectedInvoiceIds.has(invoice.id)}
                  onSelect={onSelectInvoice}
                  showSelection={true}
                />
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pending Column */}
      <Card className="border-t-4 border-t-amber-500 shadow-sm">
        <ColumnHeader 
          title="Pending" 
          count={pendingInvoices.length} 
          color="bg-amber-100 text-amber-800"
          columnInvoices={pendingInvoices}
        />
        <CardContent>
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {loadingPending ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading...</span>
              </div>
            ) : errorPending ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorPending}</AlertDescription>
              </Alert>
            ) : pendingInvoices.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No pending invoices</p>
            ) : (
              pendingInvoices.map(invoice => (
                <InvoiceCard
                  key={invoice.id}
                  invoice={invoice}
                  onViewPdf={onViewPdf}
                  isSelected={selectedInvoiceIds.has(invoice.id)}
                  onSelect={onSelectInvoice}
                  showSelection={true}
                />
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Rejected Column */}
      <Card className="border-t-4 border-t-rose-500 shadow-sm">
        <ColumnHeader 
          title="Rejected" 
          count={rejectedInvoices.length} 
          color="bg-rose-100 text-rose-800"
          columnInvoices={rejectedInvoices}
        />
        <CardContent>
          <div className="space-y-4 max-h-[600px] overflow-y-auto">
            {loadingRejected ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-muted-foreground">Loading...</span>
              </div>
            ) : errorRejected ? (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{errorRejected}</AlertDescription>
              </Alert>
            ) : rejectedInvoices.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">No rejected invoices</p>
            ) : (
              rejectedInvoices.map(invoice => (
                <InvoiceCard
                  key={invoice.id}
                  invoice={invoice}
                  onViewPdf={onViewPdf}
                  isSelected={selectedInvoiceIds.has(invoice.id)}
                  onSelect={onSelectInvoice}
                  showSelection={true}
                />
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}