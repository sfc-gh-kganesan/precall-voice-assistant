import { Button, Dialog, Flex, SingleLine, TextArea } from "@snowflake/stellar-components";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { useGenerateEmail } from "@/services/hooks";
import { useState, useEffect } from "react";
import { toast } from "sonner";

export interface ReadOnlyField {
    label: string;
    value: any;
}

export interface ReadOnlyDetailsCardProps {
    label: string;
    status?: "approved" | "pending" | "rejected";
    fields: ReadOnlyField[];
    variant?: "default" | "ai" | "warning";
    vendorName?: string | null;
    invoiceNumber?: string | null;
}

export function ReadOnlyDetailsCard(props: ReadOnlyDetailsCardProps) {
    const { label, fields, status, variant = "default", vendorName, invoiceNumber } = props;
    const [emailContent, setEmailContent] = useState<string>("");
    const [isDialogOpen, setIsDialogOpen] = useState<boolean>(false);
    const generateEmail = useGenerateEmail();

    const getVariantStyles = () => {
        switch (variant) {
            case "ai":
                return {
                    background: `linear-gradient(135deg, ${baltoTheme.statusInfoUi}10 0%, ${baltoTheme.statusInfoUi}05 100%)`,
                    borderColor: baltoTheme.statusInfoUi,
                    labelColor: baltoTheme.statusInfoUi,
                };
            case "warning":
                return {
                    background: `linear-gradient(135deg, ${baltoTheme.statusNeutralUi}10 0%, ${baltoTheme.statusNeutralUi}05 100%)`,
                    borderColor: baltoTheme.statusNeutralUi,
                    labelColor: baltoTheme.statusNeutralUi,
                };
            default:
                return {
                    background: baltoTheme.surfaceLevel_1Background,
                    borderColor: baltoTheme.reusableBorderDefault,
                    labelColor: baltoTheme.reusableTextPrimary,
                };
        }
    };

    const styles = getVariantStyles();

    // Get AI reasoning from fields
    const aiReasoningField = fields.find(field => field.label === "Reasoning");
    const aiReasoning = aiReasoningField?.value || "";

    // Handle email generation
    const handleGenerateEmail = async () => {
        if (!aiReasoning) {
            toast.error("No AI reasoning available to generate email");
            return;
        }

        try {
            const result = await generateEmail.mutateAsync({
                ai_reasoning: aiReasoning,
                vendor_name: vendorName,
                invoice_number: invoiceNumber,
            });
            
            setEmailContent(result.email_template);
            toast.success("Email template generated successfully");
        } catch (error) {
            toast.error("Failed to generate email template");
            console.error("Error generating email:", error);
        }
    };

    // Generate email when dialog opens
    useEffect(() => {
        if (isDialogOpen && !emailContent && aiReasoning) {
            handleGenerateEmail();
        }
    }, [isDialogOpen]);

    const handleDialogOpenChange = (open: boolean) => {
        setIsDialogOpen(open);
        if (!open) {
            // Reset email content when dialog closes
            setEmailContent("");
        }
    };

    return (
        <Flex
            direction="column"
            style={{
                width: "100%",
                height: "fit-content",
                rowGap: "12px",
                padding: "16px",
                border: `1px solid ${styles.borderColor}`,
                borderRadius: "8px",
                background: styles.background,
            }}
        >
            <Flex
                direction="row"
                style={{
                    justifyContent: "space-between",
                    alignItems: "center",
                }}
            >
                <SingleLine
                    style={{ fontWeight: "bolder", color: styles.labelColor }}
                >
                    {label}
                </SingleLine>
                {variant === "ai" && status === "approved" && (
                    <Button variant="primary" size="small">Send to workday</Button>
                )}
                {variant === "ai" && status === "rejected" && (
                    <Dialog.Root 
                        trigger={<Button variant="primary" size="small">Email supplier</Button>} 
                        size="medium"
                        open={isDialogOpen}
                        onOpenChange={handleDialogOpenChange}
                    >
                        <Dialog.Header heading="Email Supplier" />
                        <Dialog.Body style={{ height: "400px" }}>
                            <Flex direction="column" style={{ rowGap: "16px", height: "100%" }}>
                                <TextArea 
                                    fullWidth={true} 
                                    aria-label="Email content" 
                                    placeholder={generateEmail.isLoading ? "Generating email template..." : "Email content will appear here"}
                                    value={emailContent}
                                    onChange={(e) => setEmailContent(e.target.value)}
                                    disabled={generateEmail.isLoading}
                                    style={{ flex: 1, minHeight: "300px" }}
                                />
                            </Flex>
                        </Dialog.Body>
                        <Dialog.Footer 
                            primaryCtaArea={
                                <Flex direction="row" style={{ gap: "8px" }}>
                                    <Button 
                                        variant="secondary" 
                                        onClick={handleGenerateEmail}
                                        disabled={generateEmail.isLoading || !aiReasoning}
                                    >
                                        Regenerate
                                    </Button>
                                    <Button 
                                        variant="primary"
                                        disabled={!emailContent || generateEmail.isLoading}
                                    >
                                        Send
                                    </Button>
                                </Flex>
                            } 
                        />
                    </Dialog.Root>
                )}
            </Flex>
            <Flex direction="column" style={{ rowGap: "12px" }}>
                {fields.map((field, index) => (
                    <Flex
                        key={index}
                        direction="column"
                        style={{ rowGap: "4px" }}
                    >
                        <SingleLine
                            style={{
                                color: baltoTheme.reusableTextSecondary,
                                fontSize: "12px",
                            }}
                        >
                            {field.label}
                        </SingleLine>
                        <SingleLine
                            style={{
                                color: baltoTheme.reusableTextPrimary,
                                wordBreak: "break-word",
                                whiteSpace: "pre-wrap",
                            }}
                        >
                            {field.value ?? "—"}
                        </SingleLine>
                    </Flex>
                ))}
            </Flex>
        </Flex>
    );
}
