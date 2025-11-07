import { InvoiceResponse } from "@/services/api";
import {
    SingleLine,
    StatusBadge,
    StatusVariant,
} from "@snowflake/stellar-components";
import {
    ColumnDefinitionArray,
    DataTable,
    RowClickEvent,
} from "@snowflake/stellar-data-table";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { HighlightedText } from "./HighlightedText";

function capitalizeFirstLetter(str: string): string {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
}

export interface InvoicesTableProps {
    invoices: InvoiceResponse[];
    isLoading: boolean;
    searchString?: string;
}

export function InvoicesTable(props: InvoicesTableProps) {
    const { invoices, isLoading, searchString = "" } = props;
    const navigate = useNavigate();

    const statusMap: Record<string, Partial<StatusVariant>> = {
        approved: "success",
        pending: "info",
        rejected: "critical",
    };

    const columnDefinition: ColumnDefinitionArray<InvoiceResponse> = useMemo(
        () => [
            {
                field: "invoiceNumber",
                label: "Invoices #",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => (
                    <SingleLine style={{ fontWeight: "bolder" }}>
                        <HighlightedText
                            text={rowData?.invoice_number || ""}
                            searchString={searchString}
                        />
                    </SingleLine>
                ),
            },
            {
                field: "ticketNumber",
                label: "Lift Ticket #",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => (
                    <SingleLine>
                        <HighlightedText
                            text={rowData?.ticket_number || ""}
                            searchString={searchString}
                        />
                    </SingleLine>
                ),
            },
            {
                field: "po",
                label: "PO #",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => (
                    <SingleLine>
                        <HighlightedText
                            text={rowData?.purchase_order_number || ""}
                            searchString={searchString}
                        />
                    </SingleLine>
                ),
            },
            {
                field: "status",
                label: "Status",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => (
                    <StatusBadge
                        variant={statusMap[rowData?.status ?? "approved"]}
                        label={capitalizeFirstLetter(rowData?.status ?? "")}
                    />
                ),
            },
            {
                field: "vendor",
                label: "Vendor",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => <SingleLine>{rowData?.vendor_name}</SingleLine>,
            },
            {
                field: "amount",
                label: "Amount",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => <SingleLine>{rowData?.total_amount}</SingleLine>,
            },
            {
                field: "createdOn",
                label: "Created On",
                renderer: ({
                    rowData,
                }: {
                    rowData?: InvoiceResponse | undefined;
                }) => <SingleLine>{rowData?.created_at}</SingleLine>,
            },
        ],
        [searchString],
    );

    const handleRowClick = (event: RowClickEvent<InvoiceResponse>) => {
        navigate(
            `/invoice/${event.rowData.invoice_number}/${event.rowData.ticket_number}`,
        );
    };

    return (
        <DataTable
            isLoading={isLoading}
            density="comfortable"
            rowData={invoices}
            columnDefinition={columnDefinition}
            onRowClick={handleRowClick}
        />
    );
}
