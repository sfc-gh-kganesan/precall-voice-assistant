import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BarChart3, TrendingUp, Download, Calendar } from 'lucide-react';
import { mockMetrics } from '@/data/mockData';

const Reports = () => {
  const reportTypes = [
    { title: 'Processing Performance', description: 'Invoice processing metrics and trends', icon: TrendingUp },
    { title: 'Exception Analysis', description: 'Detailed analysis of processing exceptions', icon: BarChart3 },
    { title: 'Vendor Performance', description: 'Vendor-specific processing statistics', icon: BarChart3 },
    { title: 'Cost Savings Report', description: 'Automation impact and cost savings', icon: TrendingUp }
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports</h1>
        <p className="text-gray-600 mt-1">Analytics and insights from invoice processing</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reportTypes.map((report, index) => {
          const Icon = report.icon;
          return (
            <Card key={index}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Icon className="h-5 w-5" />
                  {report.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-gray-600">{report.description}</p>
                <div className="flex gap-2">
                  <Button size="sm">
                    <Download className="h-4 w-4 mr-2" />
                    Generate Report
                  </Button>
                  <Button variant="outline" size="sm">
                    <Calendar className="h-4 w-4 mr-2" />
                    Schedule
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Insights</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">{mockMetrics.autoProcessedPercentage}%</div>
              <div className="text-sm text-gray-600">Automation Rate</div>
              <Badge variant="secondary" className="mt-2">+5% vs last month</Badge>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{mockMetrics.averageProcessingTime}h</div>
              <div className="text-sm text-gray-600">Avg Processing Time</div>
              <Badge variant="secondary" className="mt-2">-2h vs last month</Badge>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-purple-600">${mockMetrics.totalInvoices * 1.2}k</div>
              <div className="text-sm text-gray-600">Cost Savings</div>
              <Badge variant="secondary" className="mt-2">+12% vs last month</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Reports</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Monthly Processing Summary</div>
                <div className="text-sm text-gray-600">Generated on Dec 1, 2024</div>
              </div>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <div className="font-medium">Exception Trends Analysis</div>
                <div className="text-sm text-gray-600">Generated on Nov 28, 2024</div>
              </div>
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-2" />
                Download
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Reports;