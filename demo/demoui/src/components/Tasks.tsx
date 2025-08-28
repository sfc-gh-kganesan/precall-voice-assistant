import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CheckSquare, Upload, Eye, UserCheck, BarChart3 } from 'lucide-react';
import { mockActionItems } from '@/data/mockData';

const Tasks = () => {
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

  const getActionIcon = (type: string) => {
    switch (type) {
      case 'UPLOAD':
        return <Upload className="h-4 w-4" />;
      case 'REVIEW':
        return <Eye className="h-4 w-4" />;
      case 'ASSIGN':
        return <UserCheck className="h-4 w-4" />;
      case 'REPORT':
        return <BarChart3 className="h-4 w-4" />;
      default:
        return <CheckSquare className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Tasks</h1>
        <p className="text-gray-600 mt-1">Your assigned tasks and action items</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockActionItems.map((item) => (
          <Card key={item.id}>
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  {getActionIcon(item.type)}
                  <CardTitle className="text-lg">{item.title}</CardTitle>
                </div>
                <Badge variant={getPriorityColor(item.priority)} className="text-xs">
                  {item.priority}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-gray-600">{item.description}</p>
              {item.dueDate && (
                <p className="text-sm text-orange-600">Due: {item.dueDate}</p>
              )}
              <div className="flex gap-2">
                <Button size="sm">Start Task</Button>
                <Button variant="outline" size="sm">Details</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Task Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{mockActionItems.filter(item => item.priority === 'HIGH').length}</div>
              <div className="text-sm text-gray-600">High Priority</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{mockActionItems.filter(item => item.priority === 'MEDIUM').length}</div>
              <div className="text-sm text-gray-600">Medium Priority</div>
            </div>
            <div className="text-center p-4 border rounded-lg">
              <div className="text-2xl font-bold text-green-600">{mockActionItems.filter(item => item.priority === 'LOW').length}</div>
              <div className="text-sm text-gray-600">Low Priority</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Tasks;