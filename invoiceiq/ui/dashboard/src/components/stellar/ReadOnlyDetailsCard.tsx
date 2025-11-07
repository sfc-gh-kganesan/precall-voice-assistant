import { Flex, SingleLine } from "@snowflake/stellar-components";
import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import { IconContextProvider, AiIcon } from "@snowflake/stellar-icons";

export interface ReadOnlyField {
    label: string;
    value: any;
}

export interface ReadOnlyDetailsCardProps {
    label: string;
    fields: ReadOnlyField[];
    variant?: "default" | "ai" | "warning";
}

export function ReadOnlyDetailsCard(props: ReadOnlyDetailsCardProps) {
    const { label, fields, variant = "default" } = props;

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
                {variant === "ai" && (
                    <IconContextProvider color={baltoTheme.statusInfoUi}>
                        <AiIcon />
                    </IconContextProvider>
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
