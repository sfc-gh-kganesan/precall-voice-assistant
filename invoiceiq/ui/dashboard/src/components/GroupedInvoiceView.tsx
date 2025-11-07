import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Invoice } from "./InvoiceCard";
import { InvoiceColumns } from "./InvoiceColumns";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
    Collapsible,
    CollapsibleContent,
    CollapsibleTrigger,
} from "./ui/collapsible";

interface GroupedInvoiceViewProps {
    invoices: Invoice[];
    groupBy: string;
    onViewPdf: (invoice: Invoice) => void;
    selectedInvoiceIds: Set<string>;
    onSelectInvoice: (invoiceId: string, selected: boolean) => void;
    onSelectAll: (invoiceIds: string[]) => void;
    onClearSelection: () => void;
    refreshTrigger?: number;
    optimisticUpdate?: {
        invoiceIds: string[];
        newStatus: string;
        timestamp: number;
    };
    isSearchMode?: boolean;
    searchResults?: Invoice[];
}

export function GroupedInvoiceView({
    invoices,
    groupBy,
    onViewPdf,
    selectedInvoiceIds,
    onSelectInvoice,
    onSelectAll,
    onClearSelection,
    refreshTrigger = 0,
    optimisticUpdate,
    isSearchMode = false,
    searchResults = [],
}: GroupedInvoiceViewProps) {
    const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

    if (groupBy === "none") {
        return (
            <InvoiceColumns
                onViewPdf={onViewPdf}
                selectedInvoiceIds={selectedInvoiceIds}
                onSelectInvoice={onSelectInvoice}
                onSelectAll={onSelectAll}
                onClearSelection={onClearSelection}
                refreshTrigger={refreshTrigger}
                optimisticUpdate={optimisticUpdate}
                isSearchMode={isSearchMode}
                searchResults={searchResults}
            />
        );
    }

    const groupInvoices = () => {
        const groups: { [key: string]: Invoice[] } = {};

        invoices.forEach((invoice) => {
            let key = "";
            switch (groupBy) {
                case "liftTicket":
                    key = invoice.liftTicketNumber;
                    break;
                case "purchaseOrder":
                    key = invoice.purchaseOrderNumber;
                    break;
                case "vendor":
                    key = invoice.vendor;
                    break;
                default:
                    key = "Ungrouped";
            }

            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(invoice);
        });

        return groups;
    };

    const toggleGroup = (groupName: string) => {
        const newOpenGroups = new Set(openGroups);
        if (newOpenGroups.has(groupName)) {
            newOpenGroups.delete(groupName);
        } else {
            newOpenGroups.add(groupName);
        }
        setOpenGroups(newOpenGroups);
    };

    const getGroupTitle = (key: string) => {
        switch (groupBy) {
            case "liftTicket":
                return `Lift Ticket #${key}`;
            case "purchaseOrder":
                return `Purchase Order #${key}`;
            case "vendor":
                return key;
            default:
                return key;
        }
    };

    const groupedInvoices = groupInvoices();
    const sortedGroupKeys = Object.keys(groupedInvoices).sort();

    return (
        <div className="space-y-6">
            {sortedGroupKeys.map((groupKey) => {
                const groupInvoices = groupedInvoices[groupKey];
                const isOpen = openGroups.has(groupKey);
                const approvedCount = groupInvoices.filter(
                    (inv) => inv.status === "approved",
                ).length;
                const pendingCount = groupInvoices.filter(
                    (inv) => inv.status === "pending",
                ).length;
                const rejectedCount = groupInvoices.filter(
                    (inv) => inv.status === "rejected",
                ).length;

                return (
                    <Card key={groupKey}>
                        <Collapsible
                            open={isOpen}
                            onOpenChange={() => toggleGroup(groupKey)}
                        >
                            <CollapsibleTrigger asChild>
                                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <CardTitle className="flex items-center gap-3">
                                            {isOpen ? (
                                                <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                            ) : (
                                                <ChevronRight className="w-5 h-5 text-muted-foreground" />
                                            )}
                                            {getGroupTitle(groupKey)}
                                        </CardTitle>
                                        <div className="flex items-center gap-2">
                                            <Badge variant="secondary">
                                                {groupInvoices.length} total
                                            </Badge>
                                            {approvedCount > 0 && (
                                                <Badge className="bg-emerald-100 text-emerald-800 rounded-full">
                                                    {approvedCount} approved
                                                </Badge>
                                            )}
                                            {pendingCount > 0 && (
                                                <Badge className="bg-amber-100 text-amber-800 rounded-full">
                                                    {pendingCount} pending
                                                </Badge>
                                            )}
                                            {rejectedCount > 0 && (
                                                <Badge className="bg-rose-100 text-rose-800 rounded-full">
                                                    {rejectedCount} rejected
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                </CardHeader>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                                <CardContent>
                                    <InvoiceColumns
                                        onViewPdf={onViewPdf}
                                        selectedInvoiceIds={selectedInvoiceIds}
                                        onSelectInvoice={onSelectInvoice}
                                        onSelectAll={onSelectAll}
                                        onClearSelection={onClearSelection}
                                        refreshTrigger={refreshTrigger}
                                    />
                                </CardContent>
                            </CollapsibleContent>
                        </Collapsible>
                    </Card>
                );
            })}
        </div>
    );
}
