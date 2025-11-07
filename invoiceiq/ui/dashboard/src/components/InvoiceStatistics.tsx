import { CheckCircle, Clock, TrendingUp, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface InvoiceStatisticsProps {
    totalInvoices: number;
    approvedCount: number;
    pendingCount: number;
    rejectedCount: number;
}

export function InvoiceStatistics({
    totalInvoices,
    approvedCount,
    pendingCount,
    rejectedCount,
}: InvoiceStatisticsProps) {
    const approvedPercentage =
        totalInvoices > 0 ? (approvedCount / totalInvoices) * 100 : 0;
    const pendingPercentage =
        totalInvoices > 0 ? (pendingCount / totalInvoices) * 100 : 0;
    const rejectedPercentage =
        totalInvoices > 0 ? (rejectedCount / totalInvoices) * 100 : 0;

    return (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <Card className="bg-gradient-to-br from-[var(--snowflake-blue)] to-[var(--snowflake-teal)] text-white border-0 shadow-lg">
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm opacity-90">
                        Total Invoices
                    </CardTitle>
                    <TrendingUp className="w-4 h-4 opacity-70" />
                </CardHeader>
                <CardContent>
                    <div className="text-3xl">{totalInvoices}</div>
                    <p className="text-xs opacity-80 mt-1">
                        Processed invoices
                    </p>
                </CardContent>
            </Card>

            <Card className="border-emerald-200 bg-gradient-to-br from-emerald-50 to-green-50 shadow-sm">
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm text-emerald-700">
                        Approved
                    </CardTitle>
                    <CheckCircle className="w-4 h-4 text-emerald-600" />
                </CardHeader>
                <CardContent>
                    <div className="text-3xl text-emerald-800">
                        {approvedCount}
                    </div>
                    <p className="text-xs text-emerald-600 mt-2">
                        {approvedPercentage.toFixed(1)}% of total
                    </p>
                </CardContent>
            </Card>

            <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50 shadow-sm">
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm text-amber-700">
                        Pending
                    </CardTitle>
                    <Clock className="w-4 h-4 text-amber-600" />
                </CardHeader>
                <CardContent>
                    <div className="text-3xl text-amber-800">
                        {pendingCount}
                    </div>
                    <p className="text-xs text-amber-600 mt-2">
                        {pendingPercentage.toFixed(1)}% of total
                    </p>
                </CardContent>
            </Card>

            <Card className="border-rose-200 bg-gradient-to-br from-rose-50 to-red-50 shadow-sm">
                <CardHeader className="pb-2 flex flex-row items-center justify-between">
                    <CardTitle className="text-sm text-rose-700">
                        Rejected
                    </CardTitle>
                    <XCircle className="w-4 h-4 text-rose-600" />
                </CardHeader>
                <CardContent>
                    <div className="text-3xl text-rose-800">
                        {rejectedCount}
                    </div>
                    <p className="text-xs text-rose-600 mt-2">
                        {rejectedPercentage.toFixed(1)}% of total
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
