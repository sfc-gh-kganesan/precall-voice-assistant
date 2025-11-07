import { CheckCircle, Clock, X, XCircle } from "lucide-react";
import { Invoice } from "./InvoiceCard";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";

interface BulkActionsBarProps {
    selectedCount: number;
    selectedInvoiceIds: string[];
    onBulkAction: (invoiceIds: string[], status: Invoice["status"]) => void;
    onClearSelection: () => void;
}

export function BulkActionsBar({
    selectedCount,
    selectedInvoiceIds,
    onBulkAction,
    onClearSelection,
}: BulkActionsBarProps) {
    return (
        <div className="mb-6 p-4 bg-gradient-to-r from-[var(--snowflake-light-blue)] to-blue-50 border border-[var(--snowflake-blue)]/20 rounded-xl shadow-sm">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Badge
                        variant="secondary"
                        className="bg-[var(--snowflake-blue)] text-white hover:bg-[var(--snowflake-blue)]/90"
                    >
                        {selectedCount} selected
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                        Choose an action for selected invoices:
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                            onBulkAction(selectedInvoiceIds, "approved")
                        }
                        className="flex items-center gap-2 border-green-200 text-green-700 hover:bg-green-50"
                    >
                        <CheckCircle className="w-4 h-4" />
                        Approve
                    </Button>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                            onBulkAction(selectedInvoiceIds, "pending")
                        }
                        className="flex items-center gap-2 border-yellow-200 text-yellow-700 hover:bg-yellow-50"
                    >
                        <Clock className="w-4 h-4" />
                        Pending
                    </Button>

                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                            onBulkAction(selectedInvoiceIds, "rejected")
                        }
                        className="flex items-center gap-2 border-red-200 text-red-700 hover:bg-red-50"
                    >
                        <XCircle className="w-4 h-4" />
                        Reject
                    </Button>

                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClearSelection}
                        className="ml-2"
                    >
                        <X className="w-4 h-4" />
                    </Button>
                </div>
            </div>
        </div>
    );
}
