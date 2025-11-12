import {
    Button,
    Divider,
    Flex,
    SingleLine,
} from "@snowflake/stellar-components";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import React, { useEffect, useRef, useState } from "react";
import {
    CheckCircleBoldIcon,
    EditIcon,
    IconContextProvider,
    XSmallIcon,
} from "@snowflake/stellar-icons";
import { EditableField, EditableFieldProps } from "./EditableField";
import { InvoiceResponse } from "@/services/types";
import { useUpdateInvoiceFields } from "@/services/hooks";
import { toast } from "sonner";

export interface InvoiceDetailsCardProps {
    invoice: InvoiceResponse | undefined;
    label: string;
    fields: Omit<EditableFieldProps, "onChange" | "isLoading">[];
    isLoading: boolean;
    onFieldChange: (field: keyof InvoiceResponse, value: any) => void;
}

export function InvoiceDetailsCard(props: InvoiceDetailsCardProps) {
    const { invoice, label, fields, isLoading, onFieldChange } = props;
    const [isEditing, setIsEditing] = useState(false);
    const initialFields = useRef(fields);
    const updateFields = useUpdateInvoiceFields();

    // Update initialFields when invoice data changes
    useEffect(() => {
        if (!isEditing) {
            initialFields.current = fields;
        }
    }, [fields, isEditing]);

    const handleEdit = () => {
        // Capture current field values when entering edit mode
        initialFields.current = fields;
        setIsEditing(true);
    };

    const handleCancel = () => {
        setIsEditing(false);
        initialFields.current.forEach((field) => {
            onFieldChange(field.field, field.value);
        });
    };

    const handleSave = () => {
        // Only send the fields that are part of this card, not the entire invoice
        const fieldsToUpdate: Record<string, unknown> = {};

        // Convert snake_case to camelCase for backend
        const snakeToCamel = (str: string) => {
            return str.replace(/_([a-z])/g, (_, letter) =>
                letter.toUpperCase(),
            );
        };

        fields.forEach((field) => {
            const camelCaseField = snakeToCamel(String(field.field));
            fieldsToUpdate[camelCaseField] = field.value;
        });

        updateFields.mutate({
            ticketNumber: invoice?.ticket_number ?? "",
            fields: fieldsToUpdate,
        });
    };

    useEffect(() => {
        if (updateFields.isSuccess) {
            toast.success("Fields updated successfully");
            setIsEditing(false);
            updateFields.reset();
        }
    }, [updateFields.isSuccess]);

    useEffect(() => {
        if (updateFields.isError) {
            toast.error(updateFields.error.message);
            updateFields.reset();
        }
    }, [updateFields.isError]);

    return (
        <Flex
            direction="column"
            style={{
                width: "100%",
                height: "fit-content",
                rowGap: "12px",
                padding: "16px",
                border: `1px solid ${baltoTheme.reusableBorderDefault}`,
                borderRadius: "8px",
            }}
        >
            <Flex
                direction="row"
                style={{
                    justifyContent: "space-between",
                    alignItems: "center",
                }}
            >
                <SingleLine style={{ fontWeight: "bolder" }}>
                    {label}
                </SingleLine>
                {!isEditing ? (
                    <Button
                        variant="tertiary"
                        style={{ padding: "0 8px" }}
                        onClick={handleEdit}
                    >
                        <EditIcon />
                    </Button>
                ) : (
                    <Flex
                        direction="row"
                        style={{ justifyContent: "flex-end", columnGap: "0px" }}
                    >
                        <Button
                            variant="tertiary"
                            style={{ padding: "0 8px" }}
                            onClick={handleSave}
                            isLoading={updateFields.isLoading}
                        >
                            <IconContextProvider
                                color={baltoTheme.statusSuccessUi}
                            >
                                <CheckCircleBoldIcon />
                            </IconContextProvider>
                        </Button>
                        <Button
                            variant="tertiary"
                            style={{ padding: "0 8px" }}
                            onClick={handleCancel}
                            disabled={updateFields.isLoading}
                        >
                            <XSmallIcon />
                        </Button>
                    </Flex>
                )}
            </Flex>
            <Flex direction="column" style={{ rowGap: "12px" }}>
                {fields.map((field, index) => (
                    <React.Fragment key={field.field}>
                        <EditableField
                            field={field.field}
                            label={field.label}
                            value={field.value}
                            isEditing={isEditing}
                            isLoading={isLoading}
                            onChange={(value) =>
                                onFieldChange(field.field, value)
                            }
                        />
                        {index !== fields.length - 1 && <Divider />}
                    </React.Fragment>
                ))}
            </Flex>
        </Flex>
    );
}
