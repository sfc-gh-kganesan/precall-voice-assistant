import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FileText,
  AlertTriangle,
  CheckSquare,
  BarChart3,
  X
} from 'lucide-react';

const navItems = [
  {
    to: '/',
    icon: LayoutDashboard,
    label: 'Dashboard',
    description: 'Overview and Metrics'
  },
  {
    to: '/invoice-processor',
    icon: FileText,
    label: 'Invoice Processor',
    description: 'Upload and Process'
  },
  {
    to: '/exception-queue',
    icon: AlertTriangle,
    label: 'Exception Queue',
    description: 'Review Issues'
  },
  {
    to: '/tasks',
    icon: CheckSquare,
    label: 'Tasks',
    description: 'Assigned Tasks'
  },
  {
    to: '/reports',
    icon: BarChart3,
    label: 'Reports',
    description: 'Analytics and Insights'
  }
];

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar = ({ isOpen = true, onClose }: SidebarProps) => {
  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      <aside className={cn(
        "fixed lg:static inset-y-0 left-0 w-64 bg-white border-r border-gray-200 flex flex-col h-screen z-50 transform transition-transform duration-200 ease-in-out",
        isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        <div className="p-6 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">InvoiceIQ</h2>
            <p className="text-sm text-gray-600 mt-1">AI powered AP</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="lg:hidden p-1 rounded-md hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      
      <nav className="flex-1 p-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-50 text-blue-700 border border-blue-200"
                    : "text-gray-700 hover:bg-gray-100"
                )
              }
            >
              <Icon className="h-5 w-5" />
              <div className="flex-1">
                <div className="font-medium">{item.label}</div>
                <div className="text-xs text-gray-500">{item.description}</div>
              </div>
            </NavLink>
          );
        })}
      </nav>
    </aside>
    </>
  );
};
