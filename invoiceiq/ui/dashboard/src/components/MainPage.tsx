import { useAllInvoices } from "@/services/hooks";
import { Flex, Heading } from "@snowflake/stellar-components";
import { useMemo, useState } from "react";
import { InvoiceStatistics } from "./stellar/InvoiceStatistics";
import { InvoiceControlBar } from "./stellar/InvoiceControlBar";
import { InvoicesTable } from "./stellar/InvoicesTable";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { InvoiceResponse } from "@/services/types";
import logo from "../assets/logo.svg";

/**
 * Search function that filters invoices based on invoice number, lift ticket number, and PO number
 * @param invoice - The invoice object to search
 * @param searchString - The search string to match against
 * @returns true if the invoice matches the search criteria, false otherwise
 */
function searchInvoice(invoice: InvoiceResponse, searchString: string): boolean {
    if (!searchString || searchString.trim() === "") {
        return true;
    }

    const normalizedSearch = searchString.toLowerCase().trim();

    // Search across invoice number, lift ticket number, and purchase order number
    const invoiceNumber = (invoice.invoice_number || "").toLowerCase();
    const liftTicketNumber = (invoice.ticket_number || "").toLowerCase();
    const purchaseOrderNumber = (invoice.purchase_order_number || "").toLowerCase();

    return (
        invoiceNumber.includes(normalizedSearch) ||
        liftTicketNumber.includes(normalizedSearch) ||
        purchaseOrderNumber.includes(normalizedSearch)
    );
}

export function MainPage() {
    const [status, setStatus] = useState<
        "all" | "approved" | "pending" | "rejected"
    >("all");
    const [searchString, setSearchString] = useState<string>("");

    const {
        data: invoices,
        isFetching: isLoadingInvoices,
        refetch: refetchInvoices,
    } = useAllInvoices();

    // Derive stats from invoices data
    const invoiceStats = useMemo(() => {
        if (!invoices) {
            return {
                total: 0,
                approved: 0,
                pending: 0,
                rejected: 0,
            };
        }
        return {
            total: invoices.approved.length + invoices.pending.length + invoices.rejected.length,
            approved: invoices.approved.length,
            pending: invoices.pending.length,
            rejected: invoices.rejected.length,
        };
    }, [invoices]);

    const filteredInvoices = useMemo(() => {
        if (!invoices) {
            return [];
        }

        let allInvoices: InvoiceResponse[] = [];

        switch (status) {
            case "all":
                allInvoices = [
                    ...invoices.approved,
                    ...invoices.pending,
                    ...invoices.rejected,
                ];
                break;
            case "approved":
                allInvoices = invoices.approved;
                break;
            case "pending":
                allInvoices = invoices.pending;
                break;
            case "rejected":
                allInvoices = invoices.rejected;
                break;
        }

        // Apply search filter
        return allInvoices.filter((invoice) => searchInvoice(invoice, searchString));
    }, [invoices, status, searchString]);

    const handleStatusChange = (status: string) => {
        setStatus(status as "all" | "approved" | "pending" | "rejected");
    };

    const handleSearchStringChange = (searchString: string) => {
        setSearchString(searchString);
    };

    const handleRefresh = () => {
        refetchInvoices();
    };

    return (
        <Flex
            direction="column"
            style={{
                paddingBottom: "24px",
                background: baltoTheme.surfaceLevel_1Background,
                width: "100%",
                height: "100vh",
            }}
        >
            <Flex
                direction="row"
                style={{ padding: "24px 32px 16px 32px", gap: "16px", alignItems: "center" }}
            >
                <img src={logo} alt="Logo" style={{ width: "32px", height: "32px" }} />
                <Heading size="pageHeader">InvoiceIQ Dashboard</Heading>
            </Flex>
            <Flex
                direction="column"
                style={{ rowGap: "36px", flexGrow: 1, minHeight: 0 }}
            >
                <InvoiceStatistics
                    totalInvoices={invoiceStats.total}
                    approvedCount={invoiceStats.approved}
                    pendingCount={invoiceStats.pending}
                    rejectedCount={invoiceStats.rejected}
                    isLoading={isLoadingInvoices}
                />
                <Flex
                    direction="column"
                    style={{
                        padding: "0 32px",
                        rowGap: "12px",
                        flexGrow: 1,
                        minHeight: 0,
                    }}
                >
                    <Heading size="subHeader">Invoices</Heading>
                    <InvoiceControlBar
                        status={status}
                        onStatusChange={handleStatusChange}
                        invoices={invoiceStats.total}
                        searchString={searchString}
                        onSearchStringChange={handleSearchStringChange}
                        onRefresh={handleRefresh}
                    />
                    <InvoicesTable
                        invoices={filteredInvoices}
                        isLoading={isLoadingInvoices}
                        searchString={searchString}
                    />
                </Flex>
            </Flex>
        </Flex>
    );
}
