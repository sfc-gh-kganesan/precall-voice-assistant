import { InvoiceListResponse } from "@/services/types";
import { Select, Spinner } from "@snowflake/stellar-components";
import { Component, useCallback, useEffect, useRef, useState } from "react";
import {
    Highlight,
    IHighlight,
    PdfHighlighter,
    PdfLoader,
    Popup,
} from "react-pdf-highlighter";
import pdfWorkerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

const parseIdFromHash = () =>
    document.location.hash.slice("#highlight-".length);

// Error boundary to catch PDF highlighter initialization errors
class PdfHighlighterErrorBoundary extends Component<
    { children: React.ReactNode },
    { hasError: boolean; errorCount: number }
> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false, errorCount: 0 };
    }

    static getDerivedStateFromError(_error: Error) {
        return { hasError: true };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        // Log the error but don't throw - just trigger a re-render
        console.warn("PdfHighlighter error caught:", error, errorInfo);

        // Auto-retry after a short delay
        setTimeout(() => {
            this.setState((prevState) => ({
                hasError: false,
                errorCount: prevState.errorCount + 1,
            }));
        }, 100);
    }

    render() {
        if (this.state.hasError) {
            // Show a loading spinner while recovering
            return (
                <Spinner
                    style={{
                        position: "absolute",
                        top: "45%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                    }}
                />
            );
        }

        return this.props.children;
    }
}

const HighlightPopup = ({
    comment,
}: {
    comment: { text: string; emoji: string };
}) =>
    comment.text ? (
        <div className="Highlight__popup">
            {comment.emoji} {comment.text}
        </div>
    ) : null;

interface FieldMappingTipProps {
    onConfirm: (fieldName: string) => void;
    onOpen: () => void;
}

const FieldMappingTip = ({ onConfirm, onOpen }: FieldMappingTipProps) => {
    const [selectedField, setSelectedField] = useState<string>("");

    useEffect(() => {
        onOpen();
    }, [onOpen]);

    const fieldOptions = [
        { label: "Invoice Number", value: "invoice_number" },
        { label: "Purchase Order Number", value: "purchase_order_number" },
        { label: "Invoice Date", value: "invoice_date" },
        { label: "Due Date", value: "due_date" },
        { label: "Currency", value: "invoice_currency" },
        { label: "Vendor Name", value: "vendor_name" },
        { label: "Vendor Tax ID", value: "vendor_tax_id" },
        { label: "Vendor Address", value: "vendor_address" },
        { label: "Total Amount", value: "total_amount" },
        { label: "Tax Amount", value: "tax_amount" },
        { label: "Unit Price", value: "unit_price" },
        { label: "Quantity", value: "quantity" },
        { label: "Freight/Shipping", value: "freight_shipping_amount" },
        { label: "Payment Terms", value: "payment_terms" },
        { label: "Payment Type", value: "payment_type" },
        { label: "Banking Details", value: "banking_details" },
        { label: "Service Start Date", value: "service_start_date" },
        { label: "Service End Date", value: "service_end_date" },
        { label: "Shipped To", value: "shipped_to_address" },
        { label: "Snowflake Entity", value: "snowflake_entity" },
        { label: "Snowflake Tax ID", value: "snowflake_tax_id" },
        { label: "Memo", value: "memo_description" },
    ];

    // Create a map from label to value (snake_case field name)
    const labelToValueMap: Record<string, string> = {};
    fieldOptions.forEach((option) => {
        labelToValueMap[option.label] = option.value;
    });

    const handleFieldSelect = (label: string) => {
        setSelectedField(label);
        const fieldValue = labelToValueMap[label];
        if (fieldValue) {
            onConfirm(fieldValue);
        }
    };

    return (
        <div
            style={{
                background: "white",
                padding: "8px",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            }}
        >
            <Select.Root
                value={selectedField}
                onValueChange={handleFieldSelect}
                placeholder="Add to invoice details"
                aria-label="Select field to map"
            >
                {fieldOptions.map((option) => (
                    <Select.Option key={option.value} label={option.label} />
                ))}
            </Select.Root>
        </div>
    );
};

interface InvoicePdfHighlighterProps {
    pdfUrl: string;
    invoice: InvoiceListResponse | null | undefined;
    onHighlightAdded: (highlight: IHighlight, fieldName?: string) => void;
}

export function InvoicePdfHighlighter({
    pdfUrl,
    invoice,
    onHighlightAdded,
}: InvoicePdfHighlighterProps) {
    const [highlights, setHighlights] = useState<Array<IHighlight>>([]);
    const [backendHighlightsInitialized, setBackendHighlightsInitialized] =
        useState(false);
    const [pageDimensions, setPageDimensions] = useState<
        Record<number, { width: number; height: number }>
    >({});
    const scrollViewerTo = useRef((_highlight: IHighlight) => {});

    // Get page dimensions from PDF document
    const getPageDimensions = useCallback(
        async (
            pdfDocument: any,
        ): Promise<Record<number, { width: number; height: number }>> => {
            const dims = await Promise.all(
                Array.from(
                    { length: pdfDocument.numPages },
                    (_, i) => i + 1,
                ).map(async (pageNum) => {
                    const page = await pdfDocument.getPage(pageNum);
                    const viewport = page.getViewport({ scale: 1.0 });
                    return {
                        pageNum,
                        width: viewport.width,
                        height: viewport.height,
                    };
                }),
            );

            const dimMap: Record<number, { width: number; height: number }> =
                {};
            dims.forEach((d) => {
                dimMap[d.pageNum] = { width: d.width, height: d.height };
            });

            return dimMap;
        },
        [],
    );

    // Convert backend bounding boxes to react-pdf-highlighter format
    const convertBoundingBoxesToHighlights = useCallback(
        (
            fieldsWithBoundingBoxes: Record<string, any> | null,
            pageDims: Record<number, { width: number; height: number }>,
        ): Array<IHighlight> => {
            if (!fieldsWithBoundingBoxes) return [];

            const highlights: Array<IHighlight> = [];

            Object.entries(fieldsWithBoundingBoxes).forEach(
                ([fieldName, fieldData], index) => {
                    const bbox = fieldData.bbox;
                    const page = fieldData.page;
                    const value = fieldData.value;

                    // Only create highlights for pages that are actually loaded
                    // This prevents errors when trying to highlight pages not yet rendered
                    if (!pageDims[page]) {
                        return;
                    }

                    const pageDim = pageDims[page];

                    // Backend coordinates are already in PDF points at scale 1.0
                    // Create text highlight (will render as colored box)
                    const highlight: IHighlight = {
                        id: `field-${fieldName}-${Date.now()}-${index}`,
                        position: {
                            boundingRect: {
                                x1: bbox.x0,
                                y1: bbox.y0,
                                x2: bbox.x1,
                                y2: bbox.y1,
                                width: pageDim.width,
                                height: pageDim.height,
                                pageNumber: page,
                            },
                            rects: [
                                {
                                    x1: bbox.x0,
                                    y1: bbox.y0,
                                    x2: bbox.x1,
                                    y2: bbox.y1,
                                    width: pageDim.width,
                                    height: pageDim.height,
                                    pageNumber: page,
                                },
                            ],
                            pageNumber: page,
                        },
                        content: {
                            text: value || "",
                        },
                        comment: {
                            text: "",
                            emoji: "",
                        },
                    };

                    highlights.push(highlight);
                },
            );

            return highlights;
        },
        [],
    );

    // Reset state when invoice changes
    useEffect(() => {
        setBackendHighlightsInitialized(false);
        setPageDimensions({});
        setHighlights([]);
    }, [invoice?.invoices[0]?.ticket_number]);

    // Initialize backend highlights when page dimensions are loaded
    useEffect(() => {
        if (
            !backendHighlightsInitialized &&
            Object.keys(pageDimensions).length > 0 &&
            invoice?.invoices[0]?.fields_with_bounding_boxes
        ) {
            const initialHighlights = convertBoundingBoxesToHighlights(
                invoice.invoices[0].fields_with_bounding_boxes,
                pageDimensions,
            );

            const currentManualHighlights = highlights.filter(
                (h) => !h.id.startsWith("field-"),
            );
            setHighlights([...initialHighlights, ...currentManualHighlights]);
            setBackendHighlightsInitialized(true);
        }
    }, [
        pageDimensions,
        invoice,
        backendHighlightsInitialized,
        convertBoundingBoxesToHighlights,
        highlights,
    ]);

    const resetHash = () => {
        document.location.hash = "";
    };

    const addHighlight = (
        highlight: Omit<IHighlight, "id">,
        fieldName?: string,
    ) => {
        const newHighlight: IHighlight = {
            ...highlight,
            id: String(Date.now()),
        };
        setHighlights((prevHighlights) => [...prevHighlights, newHighlight]);

        // Notify parent component
        if (onHighlightAdded) {
            onHighlightAdded(newHighlight, fieldName);
        }
    };

    const scrollToHighlightFromHash = useCallback(() => {
        const getHighlightById = (id: string) => {
            return highlights.find((highlight) => highlight.id === id);
        };

        const highlight = getHighlightById(parseIdFromHash());
        if (highlight) {
            scrollViewerTo.current(highlight);
        }
    }, [highlights]);

    return (
        <PdfLoader
            url={pdfUrl}
            workerSrc={pdfWorkerUrl}
            beforeLoad={
                <Spinner
                    style={{
                        position: "absolute",
                        top: "45%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                    }}
                />
            }
        >
            {(pdfDocument) => {
                return (
                    <PdfHighlighterErrorBoundary>
                        <PdfHighlighter
                            key={`pdf-highlighter-${invoice?.invoices[0]?.ticket_number || "none"}-${highlights.length}`}
                            pdfDocument={pdfDocument}
                            enableAreaSelection={(event) => event.altKey}
                            onScrollChange={resetHash}
                            highlights={highlights}
                            scrollRef={(scrollTo) => {
                                scrollViewerTo.current = scrollTo;
                                scrollToHighlightFromHash();

                                if (Object.keys(pageDimensions).length === 0) {
                                    setTimeout(() => {
                                        getPageDimensions(pdfDocument).then(
                                            (dimMap) => {
                                                setPageDimensions(dimMap);
                                            },
                                        );
                                    }, 100);
                                }
                            }}
                            onSelectionFinished={(
                                position,
                                content,
                                hideTipAndSelection,
                                transformSelection,
                            ) => (
                                <FieldMappingTip
                                    onOpen={transformSelection}
                                    onConfirm={(fieldName) => {
                                        addHighlight(
                                            {
                                                content,
                                                position,
                                                comment: {
                                                    text: fieldName,
                                                    emoji: "📝",
                                                },
                                            },
                                            fieldName,
                                        );
                                        hideTipAndSelection();
                                    }}
                                />
                            )}
                            highlightTransform={(
                                highlight,
                                index,
                                setTip,
                                hideTip,
                                _viewportToScaled,
                                _screenshot,
                                isScrolledTo,
                            ) => {
                                // Always use text highlight for consistency
                                // Both TEXT and OCR extractions should render the same way
                                const component = (
                                    <Highlight
                                        isScrolledTo={isScrolledTo}
                                        position={highlight.position}
                                        comment={highlight.comment}
                                    />
                                );

                                return (
                                    <Popup
                                        popupContent={
                                            <HighlightPopup {...highlight} />
                                        }
                                        onMouseOver={(popupContent) =>
                                            setTip(
                                                highlight,
                                                (_) => popupContent,
                                            )
                                        }
                                        onMouseOut={hideTip}
                                        key={index}
                                    >
                                        {component}
                                    </Popup>
                                );
                            }}
                        />
                    </PdfHighlighterErrorBoundary>
                );
            }}
        </PdfLoader>
    );
}
