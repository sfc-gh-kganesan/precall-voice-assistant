'use client'

import { useAdminStore } from '@/stores/adminStore'
import { ConfigurationList } from '@/components/admin/ConfigurationList'
import { DataSourceSelection } from '@/components/admin/DataSourceSelection'
import { FieldMapping } from '@/components/admin/FieldMapping'
import { FieldGeneration } from '@/components/admin/FieldGeneration'
import { SaveConfiguration } from '@/components/admin/SaveConfiguration'
import { RunAnalytics } from '@/components/admin/RunAnalytics'

export default function AdminPage() {
  const { currentStep } = useAdminStore()

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-primary">
              {currentStep === 0 ? 'Admin Dashboard' : 'Admin Setup'}
            </h1>
            <nav className="flex gap-6">
              <a href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </a>
              <a href="/products" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Products
              </a>
              <a href="/topics" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Topics
              </a>
              <a href="/tickets" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Cases
              </a>
              <a href="/admin" className="text-sm font-medium text-primary border-b-2 border-primary pb-1">
                Admin
              </a>
            </nav>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Progress Steps - Only show during setup wizard (steps 1-5) */}
        {currentStep > 0 && (
          <div className="mb-8">
            <div className="flex items-center justify-center space-x-2">
              {[
                { step: 1, label: 'Data Source' },
                { step: 2, label: 'Field Mapping' },
                { step: 3, label: 'Field Generation' },
                { step: 4, label: 'Save Configuration' },
                { step: 5, label: 'Run Analytics' },
              ].map((item, index) => (
                <div key={item.step} className="flex items-center">
                  <div
                    className={`
                      w-10 h-10 rounded-full flex items-center justify-center
                      ${currentStep >= item.step
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                      }
                    `}
                  >
                    {item.step}
                  </div>
                  <span className="ml-2 text-sm font-medium">
                    {item.label}
                  </span>
                  {index < 4 && (
                    <div
                      className={`
                        w-16 h-0.5 mx-2
                        ${currentStep > item.step ? 'bg-primary' : 'bg-muted'}
                      `}
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step Content */}
        <div className="max-w-4xl mx-auto">
          {currentStep === 0 && <ConfigurationList />}
          {currentStep === 1 && <DataSourceSelection />}
          {currentStep === 2 && <FieldMapping />}
          {currentStep === 3 && <FieldGeneration />}
          {currentStep === 4 && <SaveConfiguration />}
          {currentStep === 5 && <RunAnalytics />}
        </div>
      </main>
    </div>
  )
}
