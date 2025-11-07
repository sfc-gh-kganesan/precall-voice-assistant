import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import {
    Flex,
    Heading,
    SingleLine,
    SkeletonRectangle,
} from "@snowflake/stellar-components";
import {
    CheckCircleIcon,
    ClockIcon,
    ErrorCircleIcon,
    IconContextProvider,
    VectorIcon,
} from "@snowflake/stellar-icons";

export function InvoiceDataCardIcon({
    type,
}: {
    type: "total" | "approved" | "pending" | "rejected";
}) {
    switch (type) {
        case "total":
            return null;
        case "approved":
            return (
                <IconContextProvider color={baltoTheme.statusSuccessUi}>
                    <CheckCircleIcon />
                </IconContextProvider>
            );
        case "pending":
            return (
                <IconContextProvider color={baltoTheme.statusNeutralUi}>
                    <ClockIcon />
                </IconContextProvider>
            );
        case "rejected":
            return (
                <IconContextProvider color={baltoTheme.statusCriticalUi}>
                    <ErrorCircleIcon />
                </IconContextProvider>
            );
        default:
            return null;
    }
}

export interface InvoiceDataCardProps {
    type: "total" | "approved" | "pending" | "rejected";
    count: number;
    percentage: number;
    isLoading?: boolean;
}

export function InvoiceDataCard({
    type,
    count,
    percentage,
    isLoading,
}: InvoiceDataCardProps) {
    const typeMap = {
        total: "Total Invoices",
        approved: "Approved",
        pending: "Pending",
        rejected: "Rejected",
    };

    return (
        <Flex
            direction="column"
            style={{
                background: baltoTheme.surfaceLevel_2Background,
                padding: "24px",
                rowGap: "16px",
                borderRadius: "8px",
                borderWidth: 1,
                borderColor: baltoTheme.surfaceLevel_2Border,
                borderStyle: "solid",
            }}
        >
            <Flex style={{ columnGap: "8px" }}>
                <SingleLine>{typeMap[type]}</SingleLine>
                <InvoiceDataCardIcon type={type} />
            </Flex>
            <Flex direction="column" style={{ rowGap: "8px" }}>
                {isLoading ? (
                    <SkeletonRectangle width="25%" height="24px" />
                ) : (
                    <Heading size="pageHeader">
                        {count.toLocaleString()}
                    </Heading>
                )}
                {isLoading ? (
                    <SkeletonRectangle width="50%" height="16px" />
                ) : (
                    <SingleLine
                        style={{ color: baltoTheme.reusableTextSecondary }}
                    >
                        {type === "total"
                            ? "Processed"
                            : `${percentage.toFixed(1)}% of total`}
                    </SingleLine>
                )}
            </Flex>
        </Flex>
    );
}
