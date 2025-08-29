import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { 
  TrendingUp, 
  FileText, 
  AlertTriangle, 
  Clock, 
  Upload, 
  UserCheck, 
  BarChart3,
  CheckCircle,
  XCircle,
  Eye
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { mockMetrics, mockExceptions, mockActionItems } from '@/data/mockData';
import type { InvoiceException, ActionItem } from '@/types';

const Dashboard = () => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const chartData = [
    {
      name: 'Auto-processed',
      value: mockMetrics.processed.autoProcessed,
      color: '#10B981',
      icon: CheckCircle
    },
    {
      name: 'Manually reviewed',
      value: mockMetrics.processed.manuallyReviewed,
      color: '#3B82F6',
      icon: Eye
    },
    {
      name: 'Rejected',
      value: mockMetrics.processed.rejected,
      color: '#EF4444',
      icon: XCircle
    }
  ];

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-md">
          <p className="font-medium text-gray-900">{data.name}</p>
          <p className="text-sm text-gray-600">
            {data.value} invoices ({((data.value / mockMetrics.totalInvoices) * 100).toFixed(1)}%)
          </p>
        </div>
      );
    }
    return null;
  };

  const CustomLegend = () => {
    return (
      <div className="flex flex-col space-y-2">
        {chartData.map((entry, index) => {
          const Icon = entry.icon;
          return (
            <div key={index} className="flex items-center gap-2">
              <Icon className="h-4 w-4" style={{ color: entry.color }} />
              <span className="text-sm text-gray-700">{entry.name}</span>
              <span className="text-sm font-medium text-gray-900">
                {entry.value} ({((entry.value / mockMetrics.totalInvoices) * 100).toFixed(1)}%)
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  const getPriorityColor = (priority: 'HIGH' | 'MEDIUM' | 'LOW') => {
    switch (priority) {
      case 'HIGH':
        return 'destructive';
      case 'MEDIUM':
        return 'default';
      case 'LOW':
        return 'secondary';
    }
  };

  const getExceptionTypeDisplay = (type: InvoiceException['exceptionType']) => {
    switch (type) {
      case 'MISSING_PO':
        return 'Missing PO';
      case 'MISMATCH':
        return 'PO Mismatch';
      case 'DUPLICATE':
        return 'Duplicate Invoice';
      case 'INSUFFICIENT_FUNDS':
        return 'Insufficient Funds';
    }
  };

  const getActionIcon = (type: ActionItem['type']) => {
    switch (type) {
      case 'UPLOAD':
        return <Upload className="h-4 w-4" />;
      case 'REVIEW':
        return <Eye className="h-4 w-4" />;
      case 'ASSIGN':
        return <UserCheck className="h-4 w-4" />;
      case 'REPORT':
        return <BarChart3 className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Invoice Processing Dashboard</h1>
            <p className="text-gray-600 mt-1">Monitor autonomous processing, exceptions, and system performance</p>
          </div>
          <div className="text-sm text-gray-500">
            Last updated: {new Date().toLocaleString()}
          </div>
        </div>

        {/* Key Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Auto-Processed Rate</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockMetrics.autoProcessedPercentage}%</div>
              <Progress value={mockMetrics.autoProcessedPercentage} className="mt-2" />
              <p className="text-xs text-muted-foreground mt-2">
                No human intervention required
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockMetrics.totalInvoices.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">
                Processed this month
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Exceptions</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">{mockMetrics.pendingExceptions}</div>
              <p className="text-xs text-muted-foreground">
                Require human review
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Processing Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{mockMetrics.averageProcessingTime}h</div>
              <p className="text-xs text-muted-foreground">
                Per invoice
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Invoice Breakdown Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Invoice Processing Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col lg:flex-row items-center gap-6">
                <div className="flex-1 h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-shrink-0">
                  <CustomLegend />
                  <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-900">{mockMetrics.totalInvoices}</div>
                      <div className="text-sm text-gray-600">Total Invoices</div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Action Items */}
          <Card>
            <CardHeader>
              <CardTitle>Action Items</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {mockActionItems.map((item) => (
                <div key={item.id} className="flex items-start gap-3 p-3 border rounded-lg">
                  <div className="mt-0.5">
                    {getActionIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium">{item.title}</h4>
                      <Badge variant={getPriorityColor(item.priority)} className="text-xs">
                        {item.priority}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{item.description}</p>
                    {item.dueDate && (
                      <p className="text-xs text-orange-600 mt-1">Due: {item.dueDate}</p>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Pending Exceptions Table */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Pending Exceptions</CardTitle>
            <Button variant="outline" size="sm">
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Invoice Number</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Exception Type</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Date Received</TableHead>
                  <TableHead>Assigned To</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockExceptions.map((exception) => (
                  <TableRow key={exception.id}>
                    <TableCell className="font-medium">
                      <button 
                        className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                        onClick={() => window.open(exception.pdfUrl, '_blank')}
                      >
                        {exception.invoiceNumber}
                      </button>
                    </TableCell>
                    <TableCell>{exception.vendorName}</TableCell>
                    <TableCell>{formatCurrency(exception.amount)}</TableCell>
                    <TableCell>{getExceptionTypeDisplay(exception.exceptionType)}</TableCell>
                    <TableCell>
                      <Badge variant={getPriorityColor(exception.priority)}>
                        {exception.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>{exception.dateReceived}</TableCell>
                    <TableCell>{exception.assignedTo || 'Unassigned'}</TableCell>
                    <TableCell>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => window.open(exception.pdfUrl, '_blank')}
                      >
                        Review
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
    </div>
  );
};

export default Dashboard;
