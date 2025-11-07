import { baltoTheme } from "@snowflake/balto-themes/baltoTheme.stylex.js";
import {
    Button,
    ControlBar,
    SearchInput,
    Select,
    SingleLine,
} from "@snowflake/stellar-components";
import { RefreshAutoIcon, SearchIcon } from "@snowflake/stellar-icons";

export interface InvoiceControlBarProps {
    status: "all" | "approved" | "pending" | "rejected";
    onStatusChange: (status: string) => void;
    invoices: number;
    searchString: string;
    onSearchStringChange: (searchString: string) => void;
    onRefresh: () => void;
}

export function InvoiceControlBar(props: InvoiceControlBarProps) {
    const {
        status,
        onStatusChange,
        invoices,
        searchString,
        onSearchStringChange,
        onRefresh,
    } = props;

    const statusMap = {
        all: "All",
        approved: "Approved",
        pending: "Pending",
        rejected: "Rejected",
    };

    const reverseMap = {
        All: "all",
        Approved: "approved",
        Pending: "pending",
        Rejected: "rejected",
    };

    return (
        <ControlBar.Root aria-controls="invoice-control-bar">
            <ControlBar.Left>
                <Select.Root
                    prefix="Status"
                    value={statusMap[status]}
                    aria-label="Status"
                    onValueChange={(value) =>
                        onStatusChange(
                            reverseMap[value as keyof typeof reverseMap],
                        )
                    }
                >
                    <Select.Option label={statusMap["all"]} />
                    <Select.Option label={statusMap["approved"]} />
                    <Select.Option label={statusMap["pending"]} />
                    <Select.Option label={statusMap["rejected"]} />
                </Select.Root>
                <SingleLine style={{ color: baltoTheme.reusableTextSecondary }}>
                    {invoices.toLocaleString()} invoices
                </SingleLine>
            </ControlBar.Left>
            <ControlBar.Right>
                <SearchInput
                    icon={SearchIcon}
                    placeholder="Search invoices"
                    value={searchString}
                    onValueChange={onSearchStringChange}
                    style={{ minWidth: "200px", maxWidth: "400px" }}
                />
                <Button
                    aria-label="Refresh"
                    onClick={onRefresh}
                    variant="secondary"
                >
                    <RefreshAutoIcon />
                </Button>
            </ControlBar.Right>
        </ControlBar.Root>
    );
}
