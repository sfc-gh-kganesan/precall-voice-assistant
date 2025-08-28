import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertTriangle } from 'lucide-react';
import { mockExceptions } from '@/data/mockData';

const ExceptionQueue = () => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
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

  const getExceptionTypeDisplay = (type: string) => {
    switch (type) {
      case 'MISSING_PO':
        return 'Missing PO';
      case 'MISMATCH':
        return 'PO Mismatch';
      case 'DUPLICATE':
        return 'Duplicate Invoice';
      case 'INSUFFICIENT_FUNDS':
        return 'Insufficient Funds';
      default:
        return type;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Exception Queue</h1>
        <p className="text-gray-600 mt-1">Review and resolve invoice processing issues</p>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Pending Exceptions ({mockExceptions.length})
          </CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">Filter</Button>
            <Button variant="outline" size="sm">Sort</Button>
          </div>
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
                  <TableCell className="font-medium">{exception.invoiceNumber}</TableCell>
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
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">Review</Button>
                      <Button variant="outline" size="sm">Assign</Button>
                    </div>
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

export default ExceptionQueue;