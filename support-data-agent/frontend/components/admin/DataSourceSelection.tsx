'use client'

import { useQuery } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { formatNumber } from '@/lib/utils'

export function DataSourceSelection() {
  const {
    selectedDatabase,
    selectedSchema,
    selectedTables,
    setSelectedDatabase,
    setSelectedSchema,
    setSelectedTables,
    setCurrentStep,
  } = useAdminStore()

  // Fetch databases
  const { data: databases, isLoading: dbLoading } = useQuery({
    queryKey: ['databases'],
    queryFn: adminApi.getDatabases,
  })

  // Fetch schemas when database is selected
  const { data: schemas, isLoading: schemaLoading } = useQuery({
    queryKey: ['schemas', selectedDatabase],
    queryFn: () => adminApi.getSchemas(selectedDatabase!),
    enabled: !!selectedDatabase,
  })

  // Fetch tables when schema is selected
  const { data: tables, isLoading: tableLoading } = useQuery({
    queryKey: ['tables', selectedDatabase, selectedSchema],
    queryFn: () => adminApi.getTables(selectedDatabase!, selectedSchema!),
    enabled: !!selectedDatabase && !!selectedSchema,
  })

  const handleDatabaseChange = (database: string) => {
    setSelectedDatabase(database)
    setSelectedSchema(null)
    setSelectedTables([])
  }

  const handleSchemaChange = (schema: string) => {
    setSelectedSchema(schema)
    setSelectedTables([])
  }

  const handleTableToggle = (tableName: string) => {
    setSelectedTables(
      selectedTables.includes(tableName)
        ? selectedTables.filter(t => t !== tableName)
        : [...selectedTables, tableName]
    )
  }

  const canProceed = selectedDatabase && selectedSchema && selectedTables.length > 0

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">Select Data Source</h2>

      {/* Database Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium mb-2">
          Database
        </label>
        {dbLoading ? (
          <LoadingSpinner size="sm" />
        ) : (
          <select
            value={selectedDatabase || ''}
            onChange={(e) => handleDatabaseChange(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2"
          >
            <option value="">Select a database</option>
            {databases?.map((db) => (
              <option key={db} value={db}>
                {db}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Schema Selection */}
      {selectedDatabase && (
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Schema
          </label>
          {schemaLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <select
              value={selectedSchema || ''}
              onChange={(e) => handleSchemaChange(e.target.value)}
              className="w-full bg-background border border-border rounded-md px-3 py-2"
            >
              <option value="">Select a schema</option>
              {schemas?.map((schema) => (
                <option key={schema} value={schema}>
                  {schema}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* Table Selection */}
      {selectedSchema && (
        <div className="mb-6">
          <label className="block text-sm font-medium mb-2">
            Tables
          </label>
          {tableLoading ? (
            <LoadingSpinner size="sm" />
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto border border-border rounded-md p-3">
              {tables?.map((table) => (
                <label
                  key={table.name}
                  className="flex items-center justify-between p-2 hover:bg-muted rounded cursor-pointer"
                >
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      checked={selectedTables.includes(table.name)}
                      onChange={() => handleTableToggle(table.name)}
                      className="mr-3"
                    />
                    <span className="font-medium">{table.name}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {formatNumber(table.rowCount)} rows
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-end">
        <button
          onClick={() => setCurrentStep(2)}
          disabled={!canProceed}
          className="
            bg-primary text-primary-foreground px-6 py-2 rounded-md
            hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          Next: Field Mapping
        </button>
      </div>
    </div>
  )
}
