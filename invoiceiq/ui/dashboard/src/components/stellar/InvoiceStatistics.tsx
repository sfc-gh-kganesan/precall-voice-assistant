import { Grid } from "@snowflake/stellar-components";
import { InvoiceDataCard, InvoiceDataCardProps } from "./InvoiceDataCard";

export interface InvoiceStatisticsProps
    extends Pick<InvoiceDataCardProps, "isLoading"> {
    totalInvoices?: number;
    approvedCount?: number;
    pendingCount?: number;
    rejectedCount?: number;
}

export function InvoiceStatistics({
    totalInvoices = 0,
    approvedCount = 0,
    pendingCount = 0,
    rejectedCount = 0,
    ...dirtyProps
}: InvoiceStatisticsProps) {
    const approvedPercentage =
        totalInvoices > 0 ? (approvedCount / totalInvoices) * 100 : 0;
    const pendingPercentage =
        totalInvoices > 0 ? (pendingCount / totalInvoices) * 100 : 0;
    const rejectedPercentage =
        totalInvoices > 0 ? (rejectedCount / totalInvoices) * 100 : 0;

    return (
        <Grid.Root>
            <Grid.Item size={3}>
                <InvoiceDataCard
                    type="total"
                    count={totalInvoices}
                    percentage={0}
                    {...dirtyProps}
                />
            </Grid.Item>
            <Grid.Item size={3}>
                <InvoiceDataCard
                    type="pending"
                    count={pendingCount}
                    percentage={pendingPercentage}
                    {...dirtyProps}
                />
            </Grid.Item>
            <Grid.Item size={3}>
                <InvoiceDataCard
                    type="approved"
                    count={approvedCount}
                    percentage={approvedPercentage}
                    {...dirtyProps}
                />
            </Grid.Item>
            <Grid.Item size={3}>
                <InvoiceDataCard
                    type="rejected"
                    count={rejectedCount}
                    percentage={rejectedPercentage}
                    {...dirtyProps}
                />
            </Grid.Item>
        </Grid.Root>
    );
}
