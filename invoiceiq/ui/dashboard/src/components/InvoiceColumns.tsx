import { InvoiceCard, Invoice } from "./InvoiceCard";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Checkbox } from "./ui/checkbox";
import { CheckSquare, Square } from "lucide-react";

interface InvoiceColumnsProps {
  invoices: Invoice[];
  onViewPdf: (invoice: Invoice) => void;
  selectedInvoiceIds: Set<string>;
  onSelectInvoice: (invoiceId: string, selected: boolean) => void;
  onSelectAll: (invoiceIds: string[]) => void;
  onClearSelection: () => void;
}

export function InvoiceColumns({ 
  invoices, 
  onViewPdf, 
  selectedInvoiceIds, 
  onSelectInvoice, 
  onSelectAll, 
  onClearSelection 
}: InvoiceColumnsProps) {
  const approvedInvoices = invoices.filter(invoice => invoice.status === 'approved');
  const pendingInvoices = invoices.filter(invoice => invoice.status === 'pending');
  const rejectedInvoices = invoices.filter(invoice => invoice.status === 'rejected');

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
            {approvedInvoices.length === 0 ? (
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
            {pendingInvoices.length === 0 ? (
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
            {rejectedInvoices.length === 0 ? (
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