import {
    AlertCircle,
    CheckCircle,
    Clock,
    Download,
    Loader2,
    Pencil,
    RefreshCw,
    Save,
    X,
    XCircle,
    XCircle as XIcon,
} from "lucide-react";
import React, { useState, useEffect } from "react";
import { toast } from "sonner";
import {
    reprocessInvoice,
    updateInvoiceFields,
    updateInvoiceStatus,
} from "../services/api";
import { Invoice } from "./InvoiceCard";
import { Button } from "./ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "./ui/dialog";
import { Input } from "./ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "./ui/select";

interface PDFViewerProps {
    invoice: Invoice | null;
    isOpen: boolean;
    onClose: () => void;
    onUpdateStatus: (
        invoiceId: string,
        status: Invoice["status"],
        reason?: string,
    ) => void;
    onRefresh?: () => void;
}

// Helper function to format long text with line breaks (moved outside component)
const formatTextWithLineBreaks = (
    text: string | null | undefined,
    maxWords: number = 5,
): React.ReactNode => {
    if (!text) return "N/A";

    const words = text.toString().split(" ");
    if (words.length <= maxWords) {
        return text;
    }

    // Break into chunks of maxWords
    const lines: string[] = [];
    for (let i = 0; i < words.length; i += maxWords) {
        lines.push(words.slice(i, i + maxWords).join(" "));
    }

    return lines.map((line, index) => (
        <React.Fragment key={index}>
            {line}
            {index < lines.length - 1 && <br />}
        </React.Fragment>
    ));
};

// EditableField component extracted outside to prevent re-creation on every render
interface EditableFieldProps {
    label: string;
    field: keyof Invoice;
    value: any;
    sectionId: string;
    type?: string;
    isEditing: boolean;
    editedValue: any;
    onFieldChange: (field: keyof Invoice, value: any) => void;
}

const EditableField = React.memo(
    ({
        label,
        field,
        value,
        sectionId,
        type = "text",
        isEditing,
        editedValue,
        onFieldChange,
    }: EditableFieldProps) => {
        const displayValue = isEditing ? (editedValue ?? value) : value;

        return (
            <div>
                {label && (
                    <span className="text-muted-foreground">{label}:</span>
                )}
                {isEditing ? (
                    <Input
                        type={type}
                        value={displayValue || ""}
                        onChange={(e) => onFieldChange(field, e.target.value)}
                        className="h-7 text-xs mt-0.5"
                        autoFocus={false}
                    />
                ) : (
                    <p className="font-medium break-words">
                        {formatTextWithLineBreaks(displayValue)}
                    </p>
                )}
            </div>
        );
    },
);

export function PDFViewer({
    invoice,
    isOpen,
    onClose,
    onUpdateStatus,
    onRefresh,
}: PDFViewerProps) {
    const [selectedStatus, setSelectedStatus] = useState<
        Invoice["status"] | ""
    >("");
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Edit state management
    const [editingSection, setEditingSection] = useState<string | null>(null);
    const [editedValues, setEditedValues] = useState<Partial<Invoice>>({});
    const [saving, setSaving] = useState(false);
    const [hasUnsavedEdits, setHasUnsavedEdits] = useState(false);
    const [reprocessing, setReprocessing] = useState(false);

    // Local invoice state for optimistic updates
    const [localInvoice, setLocalInvoice] = useState<Invoice | null>(invoice);

    // Set PDF URL and local invoice when invoice changes
    useEffect(() => {
        if (!invoice || !isOpen) {
            setPdfUrl(null);
            setLoading(false);
            setError(null);
            setLocalInvoice(null);
            return;
        }

        // Update local invoice state
        setLocalInvoice(invoice);

        // Use the invoice PDF URL directly - backend will stream the PDF
        console.log(`Loading PDF from: ${invoice.pdfUrl}`);
        console.log("Full invoice object:", invoice);

        // Add #toolbar=0 to hide PDF toolbar and help with rendering
        const pdfUrlWithParams = invoice.pdfUrl
            ? `${invoice.pdfUrl}#toolbar=0&navpanes=0&scrollbar=0`
            : null;
        setPdfUrl(pdfUrlWithParams);
        setLoading(false);
    }, [invoice, isOpen]);

    // Reset edit state when invoice changes or modal closes
    useEffect(() => {
        setEditingSection(null);
        setEditedValues({});
        setHasUnsavedEdits(false);
    }, [invoice?.id]);

    // Reset state when modal closes
    useEffect(() => {
        if (!isOpen) {
            setHasUnsavedEdits(false);
            setReprocessing(false);
        }
    }, [isOpen]);

    // Use localInvoice for display to support optimistic updates
    const displayInvoice = localInvoice || invoice;

    if (!displayInvoice) return null;

    const handleDownload = () => {
        if (!displayInvoice) return;
        // In a real app, this would trigger a download of the PDF
        const link = document.createElement("a");
        link.href = displayInvoice.pdfUrl;
        link.download = `invoice-${displayInvoice.invoiceNumber}.pdf`;
        link.click();
    };

    const handleStatusUpdate = async () => {
        if (!displayInvoice) return;
        if (!selectedStatus || selectedStatus === displayInvoice.status) return;

        // Optimistic update - immediately update the UI
        const previousStatus = displayInvoice.status;
        setLocalInvoice((prev) =>
            prev ? { ...prev, status: selectedStatus } : null,
        );

        try {
            // Call API to update status
            await updateInvoiceStatus(
                [displayInvoice.ticketNumber],
                selectedStatus,
            );

            toast.success(`Status updated to ${selectedStatus}`);

            // Call parent's onUpdateStatus for any additional handling
            onUpdateStatus(displayInvoice.id, selectedStatus);

            // Trigger refresh to get latest data
            if (onRefresh) {
                setTimeout(() => {
                    onRefresh();
                }, 500);
            }

            setSelectedStatus("");
            onClose();
        } catch (error) {
            console.error("Error updating status:", error);
            toast.error("Failed to update status");

            // Rollback optimistic update on error
            setLocalInvoice((prev) =>
                prev ? { ...prev, status: previousStatus } : null,
            );
        }
    };

    const getStatusIcon = (status: Invoice["status"]) => {
        switch (status) {
            case "approved":
                return <CheckCircle className="w-4 h-4 text-green-600" />;
            case "pending":
                return <Clock className="w-4 h-4 text-yellow-600" />;
            case "rejected":
                return <XCircle className="w-4 h-4 text-red-600" />;
        }
    };

    const handleEditSection = (section: string) => {
        setEditingSection(section);
        // Initialize edited values with current invoice values
        setEditedValues({ ...displayInvoice });
    };

    const handleCancelEdit = () => {
        setEditingSection(null);
        setEditedValues({});
    };

    const handleFieldChange = (field: keyof Invoice, value: any) => {
        setEditedValues((prev) => ({
            ...prev,
            [field]: value,
        }));
    };

    const handleSaveSection = async (section: string) => {
        if (!displayInvoice) return;

        setSaving(true);

        // Optimistic update - immediately update the UI
        setLocalInvoice((prev) => (prev ? { ...prev, ...editedValues } : null));
        setEditingSection(null);
        const savedValues = { ...editedValues };
        setEditedValues({});

        try {
            // Call API to update invoice fields
            await updateInvoiceFields(displayInvoice.ticketNumber, savedValues);

            toast.success(`${section} updated successfully`);

            // Mark that we have unsaved edits that need agent reprocessing
            setHasUnsavedEdits(true);

            // Trigger a refresh to get the latest data from backend
            if (onRefresh) {
                setTimeout(() => {
                    onRefresh();
                }, 500); // Small delay to ensure backend has processed the update
            }
        } catch (error) {
            console.error("Error updating invoice:", error);
            toast.error(`Failed to update ${section}`);

            // Rollback optimistic update on error
            setLocalInvoice(invoice);

            // Restore editing state
            setEditingSection(section);
            setEditedValues(savedValues);
        } finally {
            setSaving(false);
        }
    };

    const handleReprocessInvoice = async () => {
        if (!displayInvoice) return;

        setReprocessing(true);

        try {
            await reprocessInvoice(displayInvoice.ticketNumber);

            toast.success("Agent workflow restarted successfully");

            // Clear the unsaved edits flag
            setHasUnsavedEdits(false);

            // Trigger a refresh to get the latest data from backend
            if (onRefresh) {
                setTimeout(() => {
                    onRefresh();
                }, 1000); // Give agent a moment to process
            }
        } catch (error) {
            console.error("Error reprocessing invoice:", error);
            toast.error("Failed to restart agent workflow");
        } finally {
            setReprocessing(false);
        }
    };

    // Helper component for section headers with edit button
    const SectionHeader = ({
        sectionId,
        title,
        color = "text-[var(--snowflake-blue)]",
        bgColor = "bg-[var(--snowflake-blue)]",
    }: {
        sectionId: string;
        title: string;
        color?: string;
        bgColor?: string;
    }) => (
        <div className="flex items-center justify-between mb-2">
            <div className="flex items-center">
                <div className={`w-1 h-4 ${bgColor} rounded-full`}></div>
                <h4 className={`font-bold ${color} text-sm`}>{title}</h4>
            </div>
            <div className="flex items-center gap-1">
                {editingSection === sectionId ? (
                    <>
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleSaveSection(title)}
                            disabled={saving}
                            className="h-6 px-2"
                        >
                            {saving ? (
                                <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                                <Save className="w-3 h-3" />
                            )}
                        </Button>
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={handleCancelEdit}
                            disabled={saving}
                            className="h-6 px-2"
                        >
                            <XIcon className="w-3 h-3" />
                        </Button>
                    </>
                ) : (
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleEditSection(sectionId)}
                        className="h-6 px-2 hover:bg-gray-100"
                    >
                        <Pencil className="w-3 h-3" />
                    </Button>
                )}
            </div>
        </div>
    );

    // Helper function to format dates without timezone issues
    const formatDateWithoutTimezone = (
        dateString: string | null | undefined,
    ): string => {
        if (!dateString) return "";

        // If it's already in YYYY-MM-DD format, just return it
        if (/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
            return dateString;
        }

        // Otherwise parse and format it
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString; // Return as-is if invalid

        // Use UTC methods to avoid timezone issues
        const year = date.getUTCFullYear();
        const month = String(date.getUTCMonth() + 1).padStart(2, "0");
        const day = String(date.getUTCDate()).padStart(2, "0");

        return `${year}-${month}-${day}`;
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent
                className="p-0 flex flex-col overflow-hidden sm:!max-w-none"
                style={{ width: "100vw", height: "100vh", maxWidth: "100vw" }}
            >
                <DialogHeader className="p-6 border-b flex-shrink-0 bg-gradient-to-r from-[var(--snowflake-light-blue)] to-white">
                    <div className="flex items-center justify-between">
                        <div>
                            <DialogTitle className="text-2xl font-bold text-[var(--snowflake-blue)]">
                                Invoice {displayInvoice.invoiceNumber || "N/A"}
                            </DialogTitle>
                            <DialogDescription className="text-base mt-1">
                                <span className="font-medium">
                                    Ticket #{displayInvoice.ticketNumber}
                                </span>
                                <span className="mx-2">•</span>
                                <span>
                                    {displayInvoice.vendorName ||
                                        "Unknown Vendor"}
                                </span>
                            </DialogDescription>
                        </div>
                        <div className="flex items-center gap-3">
                            {hasUnsavedEdits && (
                                <Button
                                    size="sm"
                                    onClick={handleReprocessInvoice}
                                    disabled={reprocessing}
                                    className="bg-gradient-to-r from-[var(--snowflake-blue)] to-[var(--snowflake-teal)] hover:from-[var(--snowflake-blue)]/90 hover:to-[var(--snowflake-teal)]/90 text-white shadow-md"
                                >
                                    {reprocessing ? (
                                        <>
                                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                            Reprocessing...
                                        </>
                                    ) : (
                                        <>
                                            <RefreshCw className="w-4 h-4 mr-2" />
                                            Rerun Agent Workflow
                                        </>
                                    )}
                                </Button>
                            )}
                            <Select
                                value={selectedStatus}
                                onValueChange={setSelectedStatus}
                            >
                                <SelectTrigger className="w-36">
                                    <SelectValue placeholder="Change status" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem
                                        value="approved"
                                        className="flex items-center gap-2"
                                    >
                                        <CheckCircle className="w-4 h-4 text-green-600" />
                                        Approved
                                    </SelectItem>
                                    <SelectItem
                                        value="pending"
                                        className="flex items-center gap-2"
                                    >
                                        <Clock className="w-4 h-4 text-yellow-600" />
                                        Pending
                                    </SelectItem>
                                    <SelectItem
                                        value="rejected"
                                        className="flex items-center gap-2"
                                    >
                                        <XCircle className="w-4 h-4 text-red-600" />
                                        Rejected
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                            {selectedStatus &&
                                selectedStatus !== displayInvoice.status && (
                                    <Button
                                        size="sm"
                                        onClick={handleStatusUpdate}
                                        className="bg-[var(--snowflake-blue)] hover:bg-[var(--snowflake-blue)]/90"
                                    >
                                        Update
                                    </Button>
                                )}
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleDownload}
                                style={{ marginRight: 30 }}
                            >
                                <Download className="w-4 h-4 mr-2" />
                                Download
                            </Button>
                        </div>
                    </div>
                </DialogHeader>

                {/* Main content area with side-by-side layout */}
                <div className="flex-1 flex overflow-hidden">
                    {/* Left side - PDF Viewer */}
                    <div
                        className="w-1/2 border-r bg-gradient-to-br from-slate-100 to-slate-50 flex items-center justify-center p-2"
                        style={{ flex: 3 }}
                    >
                        {loading && (
                            <div className="flex flex-col items-center gap-3 text-muted-foreground bg-white p-8 rounded-xl shadow-lg">
                                <Loader2 className="w-12 h-12 animate-spin text-[var(--snowflake-blue)]" />
                                <p className="text-base font-medium">
                                    Loading PDF...
                                </p>
                            </div>
                        )}

                        {error && (
                            <div className="flex flex-col items-center gap-3 bg-white p-8 rounded-xl shadow-lg border-2 border-red-200">
                                <AlertCircle className="w-12 h-12 text-red-500" />
                                <p className="font-bold text-lg text-red-600">
                                    Failed to load PDF
                                </p>
                                <p className="text-sm text-gray-600">{error}</p>
                                <a
                                    href={displayInvoice.pdfUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-[var(--snowflake-blue)] text-white rounded-lg hover:bg-[var(--snowflake-blue)]/90 transition-colors text-sm font-medium mt-2"
                                >
                                    Try opening in a new tab
                                </a>
                            </div>
                        )}

                        {!loading && !error && pdfUrl && (
                            <div className="w-full h-full flex flex-col gap-2">
                                <iframe
                                    src={`${pdfUrl}#view=FitW`}
                                    className="w-full h-full rounded-lg shadow-lg bg-white"
                                    title={`Invoice ${displayInvoice.invoiceNumber}`}
                                    style={{
                                        minHeight: "100%",
                                        border: "none",
                                    }}
                                    onLoad={() =>
                                        console.log(
                                            "PDF iframe loaded successfully!!!",
                                        )
                                    }
                                    onError={(e) => {
                                        console.error("PDF iframe error:", e);
                                        setError(
                                            "Failed to load PDF in iframe",
                                        );
                                    }}
                                />
                                <div className="flex items-center justify-center gap-2 text-xs text-gray-500 bg-white/80 p-2 rounded">
                                    <span>If PDF doesn't display,</span>
                                    <a
                                        href={displayInvoice.pdfUrl}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-[var(--snowflake-blue)] hover:underline font-medium"
                                    >
                                        open in new tab
                                    </a>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right side - Invoice Details */}
                    <div
                        className="w-1/2 overflow-y-auto p-4 bg-gradient-to-br from-gray-50 to-white"
                        style={{ flex: 1 }}
                    >
                        <div className="space-y-3">
                            {/* Basic Invoice Information */}
                            <div className="m-3 p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                <SectionHeader
                                    sectionId="invoice-info"
                                    title="Invoice Information"
                                />
                                <div className="space-y-1.5 text-xs">
                                    <EditableField
                                        label="Ticket #"
                                        field="ticketNumber"
                                        value={displayInvoice.ticketNumber}
                                        sectionId="invoice-info"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={editedValues.ticketNumber}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Invoice #"
                                        field="invoiceNumber"
                                        value={displayInvoice.invoiceNumber}
                                        sectionId="invoice-info"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={editedValues.invoiceNumber}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Purchase Order #"
                                        field="purchaseOrderNumber"
                                        value={
                                            displayInvoice.purchaseOrderNumber
                                        }
                                        sectionId="invoice-info"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={
                                            editedValues.purchaseOrderNumber
                                        }
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Invoice Date"
                                        field="invoiceDate"
                                        value={formatDateWithoutTimezone(
                                            displayInvoice.invoiceDate,
                                        )}
                                        sectionId="invoice-info"
                                        type="date"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={editedValues.invoiceDate}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Due Date"
                                        field="dueDate"
                                        value={formatDateWithoutTimezone(
                                            displayInvoice.dueDate,
                                        )}
                                        sectionId="invoice-info"
                                        type="date"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={editedValues.dueDate}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Currency"
                                        field="invoiceCurrency"
                                        value={displayInvoice.invoiceCurrency}
                                        sectionId="invoice-info"
                                        isEditing={
                                            editingSection === "invoice-info"
                                        }
                                        editedValue={
                                            editedValues.invoiceCurrency
                                        }
                                        onFieldChange={handleFieldChange}
                                    />
                                </div>
                            </div>

                            {/* Vendor Information */}
                            <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                <SectionHeader
                                    sectionId="vendor-info"
                                    title="Vendor Information"
                                />
                                <div className="space-y-1.5 text-xs">
                                    <EditableField
                                        label="Vendor Name"
                                        field="vendorName"
                                        value={displayInvoice.vendorName}
                                        sectionId="vendor-info"
                                        isEditing={
                                            editingSection === "vendor-info"
                                        }
                                        editedValue={editedValues.vendorName}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Vendor Tax ID"
                                        field="vendorTaxId"
                                        value={displayInvoice.vendorTaxId}
                                        sectionId="vendor-info"
                                        isEditing={
                                            editingSection === "vendor-info"
                                        }
                                        editedValue={editedValues.vendorTaxId}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Vendor Address"
                                        field="vendorAddress"
                                        value={displayInvoice.vendorAddress}
                                        sectionId="vendor-info"
                                        isEditing={
                                            editingSection === "vendor-info"
                                        }
                                        editedValue={editedValues.vendorAddress}
                                        onFieldChange={handleFieldChange}
                                    />
                                </div>
                            </div>

                            {/* Financial Details */}
                            <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                <SectionHeader
                                    sectionId="financial-details"
                                    title="Financial Details"
                                />
                                <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs">
                                    <EditableField
                                        label="Total Amount"
                                        field="totalAmount"
                                        value={displayInvoice.totalAmount}
                                        sectionId="financial-details"
                                        type="number"
                                        isEditing={
                                            editingSection ===
                                            "financial-details"
                                        }
                                        editedValue={editedValues.totalAmount}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Tax Amount"
                                        field="taxAmount"
                                        value={displayInvoice.taxAmount}
                                        sectionId="financial-details"
                                        type="number"
                                        isEditing={
                                            editingSection ===
                                            "financial-details"
                                        }
                                        editedValue={editedValues.taxAmount}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Unit Price"
                                        field="unitPrice"
                                        value={displayInvoice.unitPrice}
                                        sectionId="financial-details"
                                        type="number"
                                        isEditing={
                                            editingSection ===
                                            "financial-details"
                                        }
                                        editedValue={editedValues.unitPrice}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Quantity"
                                        field="quantity"
                                        value={displayInvoice.quantity}
                                        sectionId="financial-details"
                                        isEditing={
                                            editingSection ===
                                            "financial-details"
                                        }
                                        editedValue={editedValues.quantity}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Freight/Shipping"
                                        field="freightShippingAmount"
                                        value={
                                            displayInvoice.freightShippingAmount
                                        }
                                        sectionId="financial-details"
                                        type="number"
                                        isEditing={
                                            editingSection ===
                                            "financial-details"
                                        }
                                        editedValue={
                                            editedValues.freightShippingAmount
                                        }
                                        onFieldChange={handleFieldChange}
                                    />
                                    <div>
                                        <span className="text-muted-foreground">
                                            Prepaid:
                                        </span>
                                        <p className="font-medium">
                                            {displayInvoice.prepaidFlag
                                                ? "Yes"
                                                : "No"}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Payment Information */}
                            <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                <SectionHeader
                                    sectionId="payment-info"
                                    title="Payment Information"
                                />
                                <div className="space-y-1.5 text-xs">
                                    <EditableField
                                        label="Payment Terms"
                                        field="paymentTerms"
                                        value={displayInvoice.paymentTerms}
                                        sectionId="payment-info"
                                        isEditing={
                                            editingSection === "payment-info"
                                        }
                                        editedValue={editedValues.paymentTerms}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Payment Type"
                                        field="paymentType"
                                        value={displayInvoice.paymentType}
                                        sectionId="payment-info"
                                        isEditing={
                                            editingSection === "payment-info"
                                        }
                                        editedValue={editedValues.paymentType}
                                        onFieldChange={handleFieldChange}
                                    />
                                    <EditableField
                                        label="Banking Details"
                                        field="bankingDetails"
                                        value={displayInvoice.bankingDetails}
                                        sectionId="payment-info"
                                        isEditing={
                                            editingSection === "payment-info"
                                        }
                                        editedValue={
                                            editedValues.bankingDetails
                                        }
                                        onFieldChange={handleFieldChange}
                                    />
                                </div>
                            </div>

                            {/* Service/Shipping Information */}
                            {(displayInvoice.serviceStartDate ||
                                displayInvoice.serviceEndDate ||
                                displayInvoice.shippedToAddress) && (
                                <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                    <SectionHeader
                                        sectionId="service-shipping"
                                        title="Service & Shipping"
                                    />
                                    <div className="space-y-1.5 text-xs">
                                        <EditableField
                                            label="Service Start Date"
                                            field="serviceStartDate"
                                            value={formatDateWithoutTimezone(
                                                displayInvoice.serviceStartDate,
                                            )}
                                            sectionId="service-shipping"
                                            type="date"
                                            isEditing={
                                                editingSection ===
                                                "service-shipping"
                                            }
                                            editedValue={
                                                editedValues.serviceStartDate
                                            }
                                            onFieldChange={handleFieldChange}
                                        />
                                        <EditableField
                                            label="Service End Date"
                                            field="serviceEndDate"
                                            value={formatDateWithoutTimezone(
                                                displayInvoice.serviceEndDate,
                                            )}
                                            sectionId="service-shipping"
                                            type="date"
                                            isEditing={
                                                editingSection ===
                                                "service-shipping"
                                            }
                                            editedValue={
                                                editedValues.serviceEndDate
                                            }
                                            onFieldChange={handleFieldChange}
                                        />
                                        <EditableField
                                            label="Shipped To"
                                            field="shippedToAddress"
                                            value={
                                                displayInvoice.shippedToAddress
                                            }
                                            sectionId="service-shipping"
                                            isEditing={
                                                editingSection ===
                                                "service-shipping"
                                            }
                                            editedValue={
                                                editedValues.shippedToAddress
                                            }
                                            onFieldChange={handleFieldChange}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Snowflake/Tax Information */}
                            {(displayInvoice.snowflakeEntity ||
                                displayInvoice.snowflakeTaxId) && (
                                <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                    <SectionHeader
                                        sectionId="snowflake-info"
                                        title="Snowflake Information"
                                    />
                                    <div className="space-y-1.5 text-xs">
                                        <EditableField
                                            label="Snowflake Entity"
                                            field="snowflakeEntity"
                                            value={
                                                displayInvoice.snowflakeEntity
                                            }
                                            sectionId="snowflake-info"
                                            isEditing={
                                                editingSection ===
                                                "snowflake-info"
                                            }
                                            editedValue={
                                                editedValues.snowflakeEntity
                                            }
                                            onFieldChange={handleFieldChange}
                                        />
                                        <EditableField
                                            label="Snowflake Tax ID"
                                            field="snowflakeTaxId"
                                            value={
                                                displayInvoice.snowflakeTaxId
                                            }
                                            sectionId="snowflake-info"
                                            isEditing={
                                                editingSection ===
                                                "snowflake-info"
                                            }
                                            editedValue={
                                                editedValues.snowflakeTaxId
                                            }
                                            onFieldChange={handleFieldChange}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Memo/Description */}
                            {displayInvoice.memoDescription && (
                                <div className="p-3 bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                                    <SectionHeader
                                        sectionId="memo"
                                        title="Memo/Description"
                                    />
                                    <EditableField
                                        label=""
                                        field="memoDescription"
                                        value={displayInvoice.memoDescription}
                                        sectionId="memo"
                                        isEditing={editingSection === "memo"}
                                        editedValue={
                                            editedValues.memoDescription
                                        }
                                        onFieldChange={handleFieldChange}
                                    />
                                </div>
                            )}

                            {/* AI Analysis */}
                            {(displayInvoice.aiReasoning ||
                                displayInvoice.aiProcessedAt) && (
                                <div className="p-3 bg-gradient-to-br from-[var(--snowflake-blue)]/10 via-[var(--snowflake-teal)]/10 to-blue-50 border border-[var(--snowflake-blue)]/30 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-1 h-4 bg-gradient-to-b from-[var(--snowflake-blue)] to-[var(--snowflake-teal)] rounded-full"></div>
                                        <h4 className="font-bold text-[var(--snowflake-blue)] text-sm">
                                            AI Analysis
                                        </h4>
                                        <span className="ml-auto px-1.5 py-0.5 bg-[var(--snowflake-blue)] text-white text-[10px] rounded-full">
                                            AI
                                        </span>
                                    </div>
                                    {displayInvoice.aiReasoning && (
                                        <div className="mb-2">
                                            <span className="text-[10px] font-semibold text-[var(--snowflake-blue)] uppercase tracking-wide">
                                                Reasoning:
                                            </span>
                                            <p className="text-xs mt-1 p-2 bg-white/70 rounded-md leading-relaxed text-gray-700 border border-[var(--snowflake-blue)]/10">
                                                {displayInvoice.aiReasoning}
                                            </p>
                                        </div>
                                    )}
                                    {displayInvoice.aiProcessedAt && (
                                        <div>
                                            <span className="text-xs text-muted-foreground">
                                                Processed At:
                                            </span>
                                            <p className="text-xs">
                                                {new Date(
                                                    displayInvoice.aiProcessedAt,
                                                ).toLocaleString()}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Edit History */}
                            {(displayInvoice.lastEditedBy ||
                                displayInvoice.lastEditedAt) && (
                                <div className="p-3 bg-amber-50 rounded-lg shadow-sm border border-amber-200 hover:shadow-md transition-shadow">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-1 h-4 bg-amber-500 rounded-full"></div>
                                        <h4 className="font-bold text-amber-700 text-sm">
                                            Edit History
                                        </h4>
                                    </div>
                                    <div className="space-y-1.5 text-xs">
                                        <div>
                                            <span className="text-muted-foreground">
                                                Last Edited By:
                                            </span>
                                            <p className="font-medium">
                                                {displayInvoice.lastEditedBy ||
                                                    "N/A"}
                                            </p>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">
                                                Last Edited At:
                                            </span>
                                            <p className="font-medium">
                                                {displayInvoice.lastEditedAt
                                                    ? new Date(
                                                          displayInvoice.lastEditedAt,
                                                      ).toLocaleString()
                                                    : "N/A"}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
