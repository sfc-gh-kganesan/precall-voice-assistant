import { useState, useEffect } from "react";
import { InvoiceStatistics } from "./components/InvoiceStatistics";
import { InvoiceFilters } from "./components/InvoiceFilters";
import { GroupedInvoiceView } from "./components/GroupedInvoiceView";
import { PDFViewer } from "./components/PDFViewer";
import { BulkActionsBar } from "./components/BulkActionsBar";
import { Invoice } from "./components/InvoiceCard";
import { toast } from "sonner";
import { Toaster } from "./components/ui/sonner";
import { fetchInvoices, updateInvoiceStatus, searchInvoices } from "./services/api";
import { mapInvoiceResponses } from "./services/mapper";

export default function App() {
    const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
    const [selectedInvoiceIds, setSelectedInvoiceIds] = useState<Set<string>>(new Set());
    const [searchBy, setSearchBy] = useState<string>("liftTicket");
    const [searchTerm, setSearchTerm] = useState<string>("");
    const [isSearchMode, setIsSearchMode] = useState<boolean>(false);
    const [searchResults, setSearchResults] = useState<Invoice[]>([]);
    const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
    const [optimisticUpdate, setOptimisticUpdate] = useState<{ invoiceIds: string[], newStatus: string, timestamp: number } | undefined>();

    // Statistics state
    const [approvedCount, setApprovedCount] = useState<number>(0);
    const [pendingCount, setPendingCount] = useState<number>(0);
    const [rejectedCount, setRejectedCount] = useState<number>(0);
    const [totalCount, setTotalCount] = useState<number>(0);

    // Fetch statistics on mount and when refreshTrigger changes
    useEffect(() => {
        async function loadStatistics() {
            try {
                const [approvedResponse, pendingResponse, rejectedResponse] = await Promise.all([
                    fetchInvoices('approved', 1000, 0),
                    fetchInvoices('pending', 1000, 0),
                    fetchInvoices('rejected', 1000, 0),
                ]);

                setApprovedCount(approvedResponse.total_count);
                setPendingCount(pendingResponse.total_count);
                setRejectedCount(rejectedResponse.total_count);
                setTotalCount(
                    approvedResponse.total_count +
                    pendingResponse.total_count +
                    rejectedResponse.total_count
                );
            } catch (error) {
                console.error('Error loading statistics:', error);
                toast.error('Failed to load invoice statistics');
            }
        }

        loadStatistics();
    }, [refreshTrigger]);

    const handleViewPdf = (invoice: Invoice) => {
        setSelectedInvoice(invoice);
    };

    const handleClosePdf = () => {
        setSelectedInvoice(null);
    };

    const handleSearch = async () => {
        if (!searchTerm.trim()) {
            toast.error('Please enter a search term');
            return;
        }

        try {
            const response = await searchInvoices(
                searchBy as 'liftTicket' | 'purchaseOrder',
                searchTerm.trim()
            );

            const mappedInvoices = mapInvoiceResponses(response.invoices);
            setSearchResults(mappedInvoices);
            setIsSearchMode(true);

            if (mappedInvoices.length === 0) {
                toast.info('No invoices found matching your search');
            } else {
                toast.success(`Found ${mappedInvoices.length} invoice${mappedInvoices.length !== 1 ? 's' : ''}`);
            }
        } catch (error) {
            console.error('Error searching invoices:', error);
            toast.error('Failed to search invoices');
        }
    };

    const handleClearFilters = () => {
        setSearchTerm("");
        setSearchBy("liftTicket");
        setIsSearchMode(false);
        setSearchResults([]);
        setRefreshTrigger(prev => prev + 1); // Refresh to reload default view
    };

    const handleUpdateInvoiceStatus = (invoiceId: string, newStatus: Invoice['status'], reason?: string) => {
        // Clear the invoice from selection
        setSelectedInvoiceIds(prev => {
            const newSet = new Set(prev);
            newSet.delete(invoiceId);
            return newSet;
        });

        // Trigger refresh to update both invoice list and statistics
        setTimeout(() => {
            setRefreshTrigger(prev => prev + 1);
        }, 500);
    };

    const handleBulkStatusUpdate = async (invoiceIds: string[], newStatus: Invoice['status']) => {
        const count = invoiceIds.length;

        // Clear selection immediately for instant feedback
        setSelectedInvoiceIds(new Set());

        // Optimistic update: move invoices instantly in UI
        setOptimisticUpdate({ invoiceIds, newStatus, timestamp: Date.now() });

        try {
            // Call API to update status (in background)
            const response = await updateInvoiceStatus(invoiceIds, newStatus);

            // Show success message
            toast.success(`${response.updated_count} invoice${response.updated_count !== 1 ? 's' : ''} moved to ${newStatus}`);

            // After successful update, trigger refresh to sync with backend (eventual consistency)
            setTimeout(() => {
                setRefreshTrigger(prev => prev + 1);
            }, 1000); // Refresh after 1 second to confirm state

        } catch (error) {
            console.error('Error updating invoice status:', error);
            toast.error(error instanceof Error ? error.message : 'Failed to update invoice status');

            // On error, immediately refresh to rollback optimistic update
            setRefreshTrigger(prev => prev + 1);
        }
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
                    totalInvoices={totalCount}
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
                    searchBy={searchBy}
                    onSearchByChange={setSearchBy}
                    searchTerm={searchTerm}
                    onSearchChange={setSearchTerm}
                    onSearch={handleSearch}
                    onClearFilters={handleClearFilters}
                />

                {/* Invoice Columns */}
                {/* Note: Invoices are now fetched within InvoiceColumns component */}
                <GroupedInvoiceView
                    invoices={[]}
                    groupBy="none"
                    onViewPdf={handleViewPdf}
                    selectedInvoiceIds={selectedInvoiceIds}
                    onSelectInvoice={handleSelectInvoice}
                    onSelectAll={handleSelectAll}
                    onClearSelection={handleClearSelection}
                    refreshTrigger={refreshTrigger}
                    optimisticUpdate={optimisticUpdate}
                    isSearchMode={isSearchMode}
                    searchResults={searchResults}
                />

                {/* PDF Viewer */}
                <PDFViewer
                    invoice={selectedInvoice}
                    isOpen={selectedInvoice !== null}
                    onClose={handleClosePdf}
                    onUpdateStatus={handleUpdateInvoiceStatus}
                    onRefresh={() => setRefreshTrigger(prev => prev + 1)}
                />
            </div>

            {/* Toast notifications */}
            <Toaster />
        </div>
    );
}
