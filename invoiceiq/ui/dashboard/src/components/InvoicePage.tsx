import {
    downloadPdf,
    getViewPdfUrl,
    useSearchInvoices,
    useUpdateInvoiceStatus,
} from "@/services/hooks";
import { InvoiceResponse } from "@/services/types";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import {
    Button,
    Flex,
    Grid,
    Heading,
    Select,
    Spinner,
} from "@snowflake/stellar-components";
import {
    CheckCircleIcon,
    ChevronLeftBoldIcon,
    ClockIcon,
    DownloadIcon,
    ErrorCircleIcon,
    IconContextProvider,
} from "@snowflake/stellar-icons";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { InvoiceDetailsCard } from "./stellar/InvoiceDetailsCard";
import { ReadOnlyDetailsCard } from "./stellar/ReadOnlyDetailsCard";

export function InvoicePage() {
    const { invoiceNumber = "", ticketNumber = "" } = useParams();
    const navigate = useNavigate();
    const pdfUrl = getViewPdfUrl(ticketNumber);
    const {
        data: invoice,
        isFetching: isLoadingInvoice,
        refetch: refetchInvoice,
    } = useSearchInvoices("liftTicket", ticketNumber);
    const [status, setStatus] = useState<string | null>(null);
    const [showSaveButton, setShowSaveButton] = useState(false);
    const [fieldValues, setFieldValues] = useState<Record<string, any>>({});
    const updateStatus = useUpdateInvoiceStatus();

    const statusMap = {
        approved: "Approved",
        pending: "Pending",
        rejected: "Rejected",
    };

    const reverseStatusMap = {
        Approved: "approved",
        Pending: "pending",
        Rejected: "rejected",
    };

    useEffect(() => {
        if (!invoice) return;
        setStatus(invoice.invoices[0]?.status ?? null);
        setFieldValues({
            // Invoice Information
            ticket_number: invoice.invoices[0]?.ticket_number,
            invoice_number: invoice.invoices[0]?.invoice_number,
            purchase_order_number: invoice.invoices[0]?.purchase_order_number,
            invoice_date: invoice.invoices[0]?.invoice_date,
            due_date: invoice.invoices[0]?.due_date,
            invoice_currency: invoice.invoices[0]?.invoice_currency,
            // Vendor Information
            vendor_name: invoice.invoices[0]?.vendor_name,
            vendor_tax_id: invoice.invoices[0]?.vendor_tax_id,
            vendor_address: invoice.invoices[0]?.vendor_address,
            // Financial Details
            total_amount: invoice.invoices[0]?.total_amount,
            tax_amount: invoice.invoices[0]?.tax_amount,
            unit_price: invoice.invoices[0]?.unit_price,
            quantity: invoice.invoices[0]?.quantity,
            freight_shipping_amount:
                invoice.invoices[0]?.freight_shipping_amount,
            // Payment Information
            payment_terms: invoice.invoices[0]?.payment_terms,
            payment_type: invoice.invoices[0]?.payment_type,
            banking_details: invoice.invoices[0]?.banking_details,
            // Service & Shipping
            service_start_date: invoice.invoices[0]?.service_start_date,
            service_end_date: invoice.invoices[0]?.service_end_date,
            shipped_to_address: invoice.invoices[0]?.shipped_to_address,
            // Snowflake Information
            snowflake_entity: invoice.invoices[0]?.snowflake_entity,
            snowflake_tax_id: invoice.invoices[0]?.snowflake_tax_id,
            // Memo
            memo_description: invoice.invoices[0]?.memo_description,
            // AI reasoning
            ai_reasoning: invoice.invoices[0]?.ai_reasoning,
            ai_processed_at: invoice.invoices[0]?.ai_processed_at,
        });
    }, [invoice]);

    useEffect(() => {
        if (isLoadingInvoice || status === null || invoice?.invoices[0]?.status === null) return;

        if (status === invoice?.invoices[0]?.status) {
            setShowSaveButton(false);
            return;
        }

        setShowSaveButton(true);
    }, [status, invoice?.invoices[0]?.status]);

    useEffect(() => {
        if (updateStatus.isSuccess) {
            toast.success("Status updated successfully");
            updateStatus.reset();
            setShowSaveButton(false);
            refetchInvoice();
        }
    }, [updateStatus.isSuccess]);

    useEffect(() => {
        if (updateStatus.isError) {
            toast.error("Failed to update status");
            updateStatus.reset();
        }
    }, [updateStatus.isError]);

    const handleStatusChange = (value: string) => {
        setStatus(reverseStatusMap[value as keyof typeof reverseStatusMap]);
    };

    const saveStatus = () => {
        if (!invoice) return;
        updateStatus.mutate({
            ticketNumbers: [ticketNumber],
            status: status as "approved" | "pending" | "rejected",
        });
    };

    const handleFieldChange = (field: keyof InvoiceResponse, value: any) => {
        setFieldValues((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    return (
        <Flex
            direction="column"
            style={{
                height: "100vh",
                background: baltoTheme.surfaceLevel_1Background,
            }}
        >
            <Flex
                direction="row"
                style={{
                    padding: "16px 32px 16px 32px",
                    alignItems: "center",
                    borderColor: baltoTheme.surfaceLevel_1Border,
                    borderBottomWidth: "1px",
                    borderBottomStyle: "solid",
                    justifyContent: "space-between",
                }}
            >
                <Flex
                    direction="row"
                    style={{ gap: "16px", alignItems: "center" }}
                >
                    <Button
                        aria-label="Back to invoices"
                        variant="secondary"
                        onClick={() => navigate("/")}
                    >
                        <ChevronLeftBoldIcon />
                    </Button>
                    <Heading size="subHeader">Invoice #{invoiceNumber}</Heading>
                    <Heading
                        size="subHeader"
                        style={{ color: baltoTheme.reusableTextSecondary }}
                    >
                        Ticket #{ticketNumber}
                    </Heading>
                </Flex>
                <Flex
                    direction="row"
                    style={{ gap: "16px", alignItems: "center" }}
                >
                    <Button
                        aria-label="download"
                        variant="secondary"
                        onClick={() => downloadPdf(ticketNumber)}
                    >
                        <DownloadIcon />
                    </Button>
                    <Flex
                        direction="row"
                        style={{ gap: "8px", alignItems: "center" }}
                    >
                        <Select.Root
                            icon={
                                isLoadingInvoice ? null : (
                                    <IconContextProvider
                                        color={
                                            status === "approved"
                                                ? baltoTheme.statusSuccessUi
                                                : status === "pending"
                                                  ? baltoTheme.statusNeutralUi
                                                  : baltoTheme.statusCriticalUi
                                        }
                                    >
                                        {status === "approved" ? (
                                            <CheckCircleIcon />
                                        ) : status === "pending" ? (
                                            <ClockIcon />
                                        ) : (
                                            <ErrorCircleIcon />
                                        )}
                                    </IconContextProvider>
                                )
                            }
                            aria-label="status"
                            value={
                                isLoadingInvoice
                                    ? undefined
                                    : statusMap[
                                          status as keyof typeof statusMap
                                      ]
                            }
                            disabled={isLoadingInvoice}
                            onValueChange={handleStatusChange}
                        >
                            <Select.Option
                                label={statusMap["approved"]}
                                disabled={status === "approved"}
                            />
                            <Select.Option
                                label={statusMap["pending"]}
                                disabled={status === "pending"}
                            />
                            <Select.Option
                                label={statusMap["rejected"]}
                                disabled={status === "rejected"}
                            />
                        </Select.Root>
                        {showSaveButton && (
                            <Button
                                aria-label="save"
                                variant="primary"
                                isLoading={updateStatus.isLoading}
                                onClick={saveStatus}
                            >
                                Save
                            </Button>
                        )}
                    </Flex>
                </Flex>
            </Flex>
            <Grid.Root style={{ flex: 1, overflow: "hidden" }}>
                <Grid.Item size={8} style={{ position: "relative" }}>
                    <Spinner style={{ position: "absolute", top: "45%", left: "50%", transform: "translate(-50%, -50%)", zIndex: 1 }} />
                    <div
                        style={{
                            height: "100%",
                            paddingTop: "8px",
                            paddingBottom: "16px",
                            position: "relative",
                            zIndex: 10,
                        }}
                    >
                        <iframe
                            src={`${pdfUrl}#navpanes=0&scrollbar=0#view=FitW#zoom=page-fit`}
                            className="w-full h-full rounded-lg shadow-lg bg-white"
                            title={`Invoice id`}
                            style={{ minHeight: "100%", border: "none" }}
                            onLoad={() =>
                                console.log("PDF iframe loaded successfully!!!")
                            }
                            onError={(e) => {
                                console.error("PDF iframe error:", e);
                            }}
                        />
                    </div>
                </Grid.Item>
                <Grid.Item
                    size={4}
                    style={{
                        borderLeftWidth: "1px",
                        borderLeftStyle: "solid",
                        borderLeftColor: baltoTheme.surfaceLevel_1Border,
                    }}
                >
                    <Flex
                        direction="column"
                        style={{
                            paddingTop: "8px",
                            paddingBottom: "16px",
                            paddingLeft: "16px",
                            height: "calc(100vh - 88px)",
                            rowGap: "16px",
                            overflowY: "scroll",
                        }}
                    >
                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Invoice Information"
                            fields={[
                                {
                                    label: "Ticket #",
                                    field: "ticket_number",
                                    value: fieldValues.ticket_number,
                                    isEditing: false,
                                },
                                {
                                    label: "Invoice #",
                                    field: "invoice_number",
                                    value: fieldValues.invoice_number,
                                    isEditing: false,
                                },
                                {
                                    label: "Purchase Order #",
                                    field: "purchase_order_number",
                                    value: fieldValues.purchase_order_number,
                                    isEditing: false,
                                },
                                {
                                    label: "Invoice Date",
                                    field: "invoice_date",
                                    value: fieldValues.invoice_date,
                                    isEditing: false,
                                },
                                {
                                    label: "Due Date",
                                    field: "due_date",
                                    value: fieldValues.due_date,
                                    isEditing: false,
                                },
                                {
                                    label: "Currency",
                                    field: "invoice_currency",
                                    value: fieldValues.invoice_currency,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Vendor Information"
                            fields={[
                                {
                                    label: "Vendor Name",
                                    field: "vendor_name",
                                    value: fieldValues.vendor_name,
                                    isEditing: false,
                                },
                                {
                                    label: "Vendor Tax ID",
                                    field: "vendor_tax_id",
                                    value: fieldValues.vendor_tax_id,
                                    isEditing: false,
                                },
                                {
                                    label: "Vendor Address",
                                    field: "vendor_address",
                                    value: fieldValues.vendor_address,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Financial Details"
                            fields={[
                                {
                                    label: "Total Amount",
                                    field: "total_amount",
                                    value: fieldValues.total_amount,
                                    isEditing: false,
                                },
                                {
                                    label: "Tax Amount",
                                    field: "tax_amount",
                                    value: fieldValues.tax_amount,
                                    isEditing: false,
                                },
                                {
                                    label: "Unit Price",
                                    field: "unit_price",
                                    value: fieldValues.unit_price,
                                    isEditing: false,
                                },
                                {
                                    label: "Quantity",
                                    field: "quantity",
                                    value: fieldValues.quantity,
                                    isEditing: false,
                                },
                                {
                                    label: "Freight/Shipping",
                                    field: "freight_shipping_amount",
                                    value: fieldValues.freight_shipping_amount,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Payment Information"
                            fields={[
                                {
                                    label: "Payment Terms",
                                    field: "payment_terms",
                                    value: fieldValues.payment_terms,
                                    isEditing: false,
                                },
                                {
                                    label: "Payment Type",
                                    field: "payment_type",
                                    value: fieldValues.payment_type,
                                    isEditing: false,
                                },
                                {
                                    label: "Banking Details",
                                    field: "banking_details",
                                    value: fieldValues.banking_details,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Service & Shipping"
                            fields={[
                                {
                                    label: "Service Start Date",
                                    field: "service_start_date",
                                    value: fieldValues.service_start_date,
                                    isEditing: false,
                                },
                                {
                                    label: "Service End Date",
                                    field: "service_end_date",
                                    value: fieldValues.service_end_date,
                                    isEditing: false,
                                },
                                {
                                    label: "Shipped To",
                                    field: "shipped_to_address",
                                    value: fieldValues.shipped_to_address,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Snowflake Information"
                            fields={[
                                {
                                    label: "Snowflake Entity",
                                    field: "snowflake_entity",
                                    value: fieldValues.snowflake_entity,
                                    isEditing: false,
                                },
                                {
                                    label: "Snowflake Tax ID",
                                    field: "snowflake_tax_id",
                                    value: fieldValues.snowflake_tax_id,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        <InvoiceDetailsCard
                            invoice={invoice?.invoices[0]}
                            label="Memo/Description"
                            fields={[
                                {
                                    label: "Memo",
                                    field: "memo_description",
                                    value: fieldValues.memo_description,
                                    isEditing: false,
                                },
                            ]}
                            isLoading={isLoadingInvoice}
                            onFieldChange={handleFieldChange}
                        />

                        {(invoice?.invoices[0]?.ai_reasoning ||
                            invoice?.invoices[0]?.ai_processed_at) && (
                            <ReadOnlyDetailsCard
                                label="AI Analysis"
                                variant="ai"
                                fields={[
                                    ...(invoice?.invoices[0]?.ai_reasoning
                                        ? [
                                              {
                                                  label: "Reasoning",
                                                  value: invoice.invoices[0]
                                                      .ai_reasoning,
                                              },
                                          ]
                                        : []),
                                    ...(invoice?.invoices[0]?.ai_processed_at
                                        ? [
                                              {
                                                  label: "Processed At",
                                                  value: new Date(
                                                      invoice.invoices[0].ai_processed_at,
                                                  ).toLocaleString(),
                                              },
                                          ]
                                        : []),
                                ]}
                            />
                        )}

                        {(invoice?.invoices[0]?.last_edited_by ||
                            invoice?.invoices[0]?.last_edited_at) && (
                            <ReadOnlyDetailsCard
                                label="Edit History"
                                variant="warning"
                                fields={[
                                    {
                                        label: "Last Edited By",
                                        value:
                                            invoice?.invoices[0]
                                                ?.last_edited_by || "N/A",
                                    },
                                    {
                                        label: "Last Edited At",
                                        value: invoice?.invoices[0]
                                            ?.last_edited_at
                                            ? new Date(
                                                  invoice.invoices[0].last_edited_at,
                                              ).toLocaleString()
                                            : "N/A",
                                    },
                                ]}
                            />
                        )}
                    </Flex>
                </Grid.Item>
            </Grid.Root>
        </Flex>
    );
}
