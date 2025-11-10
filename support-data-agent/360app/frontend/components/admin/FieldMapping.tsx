'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { PreviewTable } from '@/components/admin/PreviewTable'
import { FieldMapping as FieldMappingType } from '@/types'

const REQUIRED_FIELDS = [
  { field: 'case_id', label: 'Case ID', description: 'Unique case identifier' },
  { field: 'subject', label: 'Subject', description: 'Case subject/title' },
  { field: 'description', label: 'Description', description: 'Case description/body' },
  { field: 'created_at', label: 'Created At', description: 'When the case was created' },
  { field: 'topic', label: 'Topic', description: 'Main subject of the case' },
  { field: 'product', label: 'Product', description: 'Product related to the case' },
] as const

export function FieldMapping() {
  const {
    selectedDatabase,
    selectedSchema,
    selectedTables,
    fieldMappings,
    setFieldMappings,
    setCurrentStep,
  } = useAdminStore()

  const [localMappings, setLocalMappings] = useState<FieldMappingType[]>(
    fieldMappings.length > 0 ? fieldMappings :
    REQUIRED_FIELDS.map(f => ({
      targetField: f.field as unknown as FieldMappingType['targetField'],
      sourceType: 'column',
      sourceColumn: undefined,
      sourceColumns: [],
      aiInstruction: '',
    }))
  )

  // Fetch preview data (includes both columns and rows)
  const { data: preview, isLoading: previewLoading } = useQuery({
    queryKey: ['preview', selectedDatabase, selectedSchema, selectedTables[0]],
    queryFn: () => adminApi.getTablePreview(
      selectedDatabase!,
      selectedSchema!,
      selectedTables[0]
    ),
    enabled: !!selectedDatabase && !!selectedSchema && selectedTables.length > 0,
  })

  // Use preview columns for consistency between dropdown and preview table
  const columns = preview?.columns || []
  const columnsLoading = previewLoading

  const handleMappingChange = (index: number, mapping: Partial<FieldMappingType>) => {
    const updated = [...localMappings]
    updated[index] = { ...updated[index], ...mapping }
    setLocalMappings(updated)
  }

  const handleColumnToggle = (index: number, column: string) => {
    const updated = [...localMappings]
    const currentColumns = updated[index].sourceColumns || []
    updated[index].sourceColumns = currentColumns.includes(column)
      ? currentColumns.filter(c => c !== column)
      : [...currentColumns, column]
    setLocalMappings(updated)
  }

  const canProceed = localMappings.every(m =>
    m.sourceType === 'generated' || (m.sourceType === 'column' && m.sourceColumn)
  )

  const handleNext = () => {
    setFieldMappings(localMappings)
    setCurrentStep(3)
  }

  // Get highlighted columns for preview
  const highlightedColumns = localMappings
    .filter(m => m.sourceType === 'column' && m.sourceColumn)
    .map(m => m.sourceColumn!)
    .concat(
      localMappings
        .filter(m => m.sourceType === 'generated')
        .flatMap(m => m.sourceColumns || [])
    )

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-2">Map Required Fields</h2>
      <div className="text-sm text-muted-foreground mb-6">
        {selectedDatabase}.{selectedSchema}.{selectedTables[0]}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Field Mappings */}
        <div>
          <h3 className="text-sm font-medium mb-4">Field Configuration</h3>
          {columnsLoading ? (
            <LoadingSpinner size="md" className="h-48" />
          ) : (
            <div className="space-y-4">
              {REQUIRED_FIELDS.map((field, index) => (
                <div key={field.field} className="border border-border rounded-lg p-4">
                  <div className="mb-3">
                    <h4 className="font-medium text-sm">{field.label}</h4>
                    <p className="text-xs text-muted-foreground">{field.description}</p>
                  </div>

                  <div className="space-y-3">
                    {/* Source Type Selection */}
                    <div className="flex gap-4">
                      <label className="flex items-center text-sm">
                        <input
                          type="radio"
                          name={`source-${field.field}`}
                          checked={localMappings[index]?.sourceType === 'column'}
                          onChange={() => handleMappingChange(index, { sourceType: 'column' })}
                          className="mr-2"
                        />
                        Map to column
                      </label>
                      <label className="flex items-center text-sm">
                        <input
                          type="radio"
                          name={`source-${field.field}`}
                          checked={localMappings[index]?.sourceType === 'generated'}
                          onChange={() => handleMappingChange(index, { sourceType: 'generated' })}
                          className="mr-2"
                        />
                        Generate with AI
                      </label>
                    </div>

                    {/* Column Selection */}
                    {localMappings[index]?.sourceType === 'column' && (
                      <select
                        value={localMappings[index]?.sourceColumn || ''}
                        onChange={(e) => handleMappingChange(index, { sourceColumn: e.target.value })}
                        className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
                      >
                        <option value="">Select a column</option>
                        {columns?.map((col) => (
                          <option key={col} value={col}>
                            {col}
                          </option>
                        ))}
                      </select>
                    )}

                    {/* AI Generation Configuration */}
                    {localMappings[index]?.sourceType === 'generated' && (
                      <div className="space-y-3 bg-muted/50 rounded-md p-3">
                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-2 block">
                            Source columns for context
                          </label>
                          <div className="space-y-1 max-h-32 overflow-y-auto">
                            {columns?.map((col) => (
                              <label key={col} className="flex items-center text-sm">
                                <input
                                  type="checkbox"
                                  checked={localMappings[index]?.sourceColumns?.includes(col) || false}
                                  onChange={() => handleColumnToggle(index, col)}
                                  className="mr-2"
                                />
                                {col}
                              </label>
                            ))}
                          </div>
                        </div>

                        <div>
                          <label className="text-xs font-medium text-muted-foreground mb-2 block">
                            AI Instruction
                          </label>
                          <input
                            type="text"
                            value={localMappings[index]?.aiInstruction || ''}
                            onChange={(e) => handleMappingChange(index, { aiInstruction: e.target.value })}
                            placeholder="e.g., Extract product name from description"
                            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
                          />
                        </div>

                        {localMappings[index]?.sourceColumns && localMappings[index].sourceColumns!.length > 0 && localMappings[index]?.aiInstruction && (
                          <div className="text-xs text-muted-foreground bg-background rounded-md p-2 border border-border">
                            <span className="font-medium">Preview: </span>
                            Use {localMappings[index].sourceColumns!.join(', ')} to: {localMappings[index].aiInstruction}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Data Preview */}
        <div>
          <h3 className="text-sm font-medium mb-4">Data Preview</h3>
          <PreviewTable
            columns={preview?.columns || []}
            rows={preview?.rows || []}
            isLoading={previewLoading}
            highlightedColumns={highlightedColumns}
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between mt-8">
        <button
          onClick={() => setCurrentStep(1)}
          className="px-6 py-2 border border-border rounded-md hover:bg-muted"
        >
          Back
        </button>
        <button
          onClick={handleNext}
          disabled={!canProceed}
          className="
            bg-primary text-primary-foreground px-6 py-2 rounded-md
            hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          Next: Field Generation
        </button>
      </div>
    </div>
  )
}
