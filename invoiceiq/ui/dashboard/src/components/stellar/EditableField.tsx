import {
    Flex,
    SingleLine,
    SkeletonRectangle,
    TextInput,
} from "@snowflake/stellar-components";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { InvoiceResponse } from "@/services/types";

export interface EditableFieldProps {
    label: string;
    field: keyof InvoiceResponse;
    value: any;
    isEditing: boolean;
    isLoading: boolean;
    onChange: (value: any) => void;
}

export function EditableField(props: EditableFieldProps) {
    const { label, value, isEditing, isLoading, onChange } = props;

    return (
        <Flex direction="column" style={{ rowGap: "8px" }}>
            <SingleLine style={{ color: baltoTheme.reusableTextSecondary }}>
                {label}
            </SingleLine>
            {isLoading ? (
                <SkeletonRectangle width="80%" height="16px" />
            ) : isEditing ? (
                <TextInput
                    aria-label={label}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                />
            ) : (
                <SingleLine>{value ?? "—"}</SingleLine>
            )}
        </Flex>
    );
}
