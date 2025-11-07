import { AlertCircle, Loader2 } from "lucide-react";
import React, { useState, useEffect } from "react";
import { fetchAllInvoices } from "../services/api";
import { mapInvoiceResponses } from "../services/mapper";
import { Invoice, InvoiceCard } from "./InvoiceCard";
import { Alert, AlertDescription } from "./ui/alert";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Checkbox } from "./ui/checkbox";

interface InvoiceColumnsProps {
    onViewPdf: (invoice: Invoice) => void;
    selectedInvoiceIds: Set<string>;
    onSelectInvoice: (invoiceId: string, selected: boolean) => void;
    onSelectAll: (invoiceIds: string[]) => void;
    onClearSelection: () => void;
    refreshTrigger?: number; // Optional prop to trigger refresh
    optimisticUpdate?: {
        invoiceIds: string[];
        newStatus: string;
        timestamp: number;
    }; // For instant UI updates
    silentRefresh?: boolean; // If true, refresh without showing loading state
    isSearchMode?: boolean; // If true, display search results instead of fetching
    searchResults?: Invoice[]; // Search results to display
}

export function InvoiceColumns({
    onViewPdf,
    selectedInvoiceIds,
    onSelectInvoice,
    onSelectAll,
    refreshTrigger = 0,
    optimisticUpdate,
    silentRefresh = false,
    isSearchMode = false,
    searchResults = [],
}: InvoiceColumnsProps) {
    const [approvedInvoices, setApprovedInvoices] = useState<Invoice[]>([]);
    const [pendingInvoices, setPendingInvoices] = useState<Invoice[]>([]);
    const [rejectedInvoices, setRejectedInvoices] = useState<Invoice[]>([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // No longer need to set state based on search results - we use them directly in render
    // This prevents any race conditions or state update issues

    // Handle optimistic updates - move invoices instantly
    useEffect(() => {
        // Skip optimistic updates in search mode
        if (isSearchMode || !optimisticUpdate) return;

        const { invoiceIds, newStatus } = optimisticUpdate;
        const idSet = new Set(invoiceIds);

        // Collect invoices to move from all columns
        const allInvoices = [
            ...approvedInvoices,
            ...pendingInvoices,
            ...rejectedInvoices,
        ];
        const toMove = allInvoices.filter((inv) => idSet.has(inv.id));

        if (toMove.length === 0) return;

        // Update status of moved invoices
        const movedInvoices = toMove.map((inv) => ({
            ...inv,
            status: newStatus as Invoice["status"],
        }));

        // Remove from all columns and add to target column
        setApprovedInvoices((prev) => {
            const filtered = prev.filter((inv) => !idSet.has(inv.id));
            return newStatus === "approved"
                ? [
                      ...filtered,
                      ...movedInvoices.filter((i) => i.status === "approved"),
                  ]
                : filtered;
        });

        setPendingInvoices((prev) => {
            const filtered = prev.filter((inv) => !idSet.has(inv.id));
            return newStatus === "pending"
                ? [
                      ...filtered,
                      ...movedInvoices.filter((i) => i.status === "pending"),
                  ]
                : filtered;
        });

        setRejectedInvoices((prev) => {
            const filtered = prev.filter((inv) => !idSet.has(inv.id));
            return newStatus === "rejected"
                ? [
                      ...filtered,
                      ...movedInvoices.filter((i) => i.status === "rejected"),
                  ]
                : filtered;
        });
    }, [optimisticUpdate, isSearchMode]);

    // Fetch all invoices in a single optimized query
    useEffect(() => {
        let isMounted = true;

        async function loadAllInvoices() {
            // Check search mode at the start - if in search mode, don't fetch
            if (isSearchMode) {
                console.log("[FETCH ALL] Skipped - in search mode");
                return;
            }

            try {
                if (!silentRefresh) {
                    setLoading(true);
                }
                setError(null);
                console.log("[FETCH ALL] Starting optimized fetch...");

                // Single API call to fetch all invoices grouped by status
                const response = await fetchAllInvoices(100);

                // Double-check we're still mounted AND not in search mode before updating state
                if (isMounted && !isSearchMode) {
                    console.log("[FETCH ALL] Setting invoices:", {
                        approved: response.approved.length,
                        pending: response.pending.length,
                        rejected: response.rejected.length,
                    });

                    // Map and set all invoice lists at once
                    setApprovedInvoices(mapInvoiceResponses(response.approved));
                    setPendingInvoices(mapInvoiceResponses(response.pending));
                    setRejectedInvoices(mapInvoiceResponses(response.rejected));
                } else {
                    console.log(
                        "[FETCH ALL] Discarding results - unmounted or in search mode",
                    );
                }
            } catch (err) {
                if (isMounted && !isSearchMode) {
                    const errorMessage =
                        err instanceof Error
                            ? err.message
                            : "Failed to load invoices";
                    console.error("[FETCH ALL] Error:", errorMessage);
                    setError(errorMessage);
                }
            } finally {
                if (isMounted && !silentRefresh && !isSearchMode) {
                    setLoading(false);
                }
            }
        }

        loadAllInvoices();
        return () => {
            isMounted = false;
        };
    }, [refreshTrigger, silentRefresh, isSearchMode]);

    const getColumnInvoiceIds = (columnInvoices: Invoice[]) =>
        columnInvoices.map((inv) => inv.id);

    const getSelectedCountInColumn = (columnInvoices: Invoice[]) =>
        columnInvoices.filter((inv) => selectedInvoiceIds.has(inv.id)).length;

    const isAllSelectedInColumn = (columnInvoices: Invoice[]) =>
        columnInvoices.length > 0 &&
        getSelectedCountInColumn(columnInvoices) === columnInvoices.length;

    const handleSelectAllInColumn = (columnInvoices: Invoice[]) => {
        const columnIds = getColumnInvoiceIds(columnInvoices);
        if (isAllSelectedInColumn(columnInvoices)) {
            // Deselect all in this column
            columnIds.forEach((id) => onSelectInvoice(id, false));
        } else {
            // Select all in this column
            onSelectAll(columnIds);
        }
    };

    const ColumnHeader = ({
        title,
        count,
        color,
        columnInvoices,
    }: {
        title: string;
        count: number;
        color: string;
        columnInvoices: Invoice[];
    }) => {
        const selectedCount = getSelectedCountInColumn(columnInvoices);
        const allSelected = isAllSelectedInColumn(columnInvoices);
        const someSelected =
            selectedCount > 0 && selectedCount < columnInvoices.length;

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
                                    onCheckedChange={() =>
                                        handleSelectAllInColumn(columnInvoices)
                                    }
                                    className="data-[state=checked]:bg-[var(--snowflake-blue)] data-[state=checked]:border-[var(--snowflake-blue)]"
                                />
                            )}
                            {title}
                        </div>
                        <Badge
                            variant="secondary"
                            className={`${color} rounded-full`}
                        >
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

    // MOST MANUAL APPROACH: When in search mode, completely ignore fetched data
    // and ONLY use search results organized by status
    const displayApprovedInvoices = isSearchMode
        ? searchResults.filter((inv) => inv.status === "approved")
        : approvedInvoices;

    const displayPendingInvoices = isSearchMode
        ? searchResults.filter((inv) => inv.status === "pending")
        : pendingInvoices;

    const displayRejectedInvoices = isSearchMode
        ? searchResults.filter((inv) => inv.status === "rejected")
        : rejectedInvoices;

    console.log("[RENDER] isSearchMode:", isSearchMode);
    console.log("[RENDER] Displaying:", {
        approved: displayApprovedInvoices.length,
        pending: displayPendingInvoices.length,
        rejected: displayRejectedInvoices.length,
    });

    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Approved Column */}
            <Card className="border-t-4 border-t-emerald-500 shadow-sm">
                <ColumnHeader
                    title="Approved"
                    count={displayApprovedInvoices.length}
                    color="bg-emerald-100 text-emerald-800"
                    columnInvoices={displayApprovedInvoices}
                />
                <CardContent>
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                        {loading && !isSearchMode ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                <span className="ml-2 text-muted-foreground">
                                    Loading...
                                </span>
                            </div>
                        ) : error ? (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        ) : displayApprovedInvoices.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">
                                No approved invoices
                            </p>
                        ) : (
                            displayApprovedInvoices.map((invoice) => (
                                <InvoiceCard
                                    key={invoice.id}
                                    invoice={invoice}
                                    onViewPdf={onViewPdf}
                                    isSelected={selectedInvoiceIds.has(
                                        invoice.id,
                                    )}
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
                    count={displayPendingInvoices.length}
                    color="bg-amber-100 text-amber-800"
                    columnInvoices={displayPendingInvoices}
                />
                <CardContent>
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                        {loading && !isSearchMode ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                <span className="ml-2 text-muted-foreground">
                                    Loading...
                                </span>
                            </div>
                        ) : error ? (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        ) : displayPendingInvoices.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">
                                No pending invoices
                            </p>
                        ) : (
                            displayPendingInvoices.map((invoice) => (
                                <InvoiceCard
                                    key={invoice.id}
                                    invoice={invoice}
                                    onViewPdf={onViewPdf}
                                    isSelected={selectedInvoiceIds.has(
                                        invoice.id,
                                    )}
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
                    count={displayRejectedInvoices.length}
                    color="bg-rose-100 text-rose-800"
                    columnInvoices={displayRejectedInvoices}
                />
                <CardContent>
                    <div className="space-y-4 max-h-[600px] overflow-y-auto">
                        {loading && !isSearchMode ? (
                            <div className="flex items-center justify-center py-8">
                                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                                <span className="ml-2 text-muted-foreground">
                                    Loading...
                                </span>
                            </div>
                        ) : error ? (
                            <Alert variant="destructive">
                                <AlertCircle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        ) : displayRejectedInvoices.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">
                                No rejected invoices
                            </p>
                        ) : (
                            displayRejectedInvoices.map((invoice) => (
                                <InvoiceCard
                                    key={invoice.id}
                                    invoice={invoice}
                                    onViewPdf={onViewPdf}
                                    isSelected={selectedInvoiceIds.has(
                                        invoice.id,
                                    )}
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
