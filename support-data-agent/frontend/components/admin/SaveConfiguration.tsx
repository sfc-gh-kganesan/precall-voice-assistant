'use client'

import { useMutation } from '@tanstack/react-query'
import { useAdminStore } from '@/stores/adminStore'
import { adminApi } from '@/services/api'

export function SaveConfiguration() {
  const {
    selectedDatabase,
    selectedSchema,
    selectedTables,
    fieldMappings,
    configurationName,
    outputTableName,
    setConfigurationName,
    setOutputTableName,
    setConfigurationId,
    setCurrentStep,
  } = useAdminStore()

  const saveConfig = useMutation({
    mutationFn: () => adminApi.saveConfiguration({
      name: configurationName || `${selectedDatabase}.${selectedSchema} Configuration`,
      database: selectedDatabase!,
      schema: selectedSchema!,
      tables: selectedTables,
      mappings: fieldMappings,
      outputTable: outputTableName || selectedTables[0]
    }),
    onSuccess: (data) => {
      setConfigurationId(data.configId)
      setCurrentStep(5)
    },
  })

  const handleSave = () => {
    if (!configurationName) {
      setConfigurationName(`${selectedDatabase}.${selectedSchema} Configuration`)
    }
    if (!outputTableName) {
      setOutputTableName(selectedTables[0])
    }
    saveConfig.mutate()
  }

  const handleStartOver = () => {
    if (confirm('Are you sure? This will discard your current configuration.')) {
      setCurrentStep(1)
    }
  }

  const mappedFields = fieldMappings.filter(m => m.sourceType === 'column')
  const generatedFields = fieldMappings.filter(m => m.sourceType === 'generated')

  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-6">Save Configuration</h2>

      {/* Configuration Name & Output Table */}
      <div className="mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Configuration Name</label>
          <input
            type="text"
            value={configurationName}
            onChange={(e) => setConfigurationName(e.target.value)}
            placeholder={`${selectedDatabase}.${selectedSchema} Configuration`}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Output Table Name</label>
          <input
            type="text"
            value={outputTableName}
            onChange={(e) => setOutputTableName(e.target.value)}
            placeholder={selectedTables[0]}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Full path: {selectedDatabase}.{selectedSchema}.{outputTableName || selectedTables[0]}
          </p>
        </div>
      </div>

      {/* Configuration Summary */}
      <div className="space-y-4 mb-8">
        <div className="bg-muted rounded-lg p-4">
          <h3 className="font-medium mb-3">Configuration Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Database</span>
              <span className="font-medium">{selectedDatabase}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Schema</span>
              <span className="font-medium">{selectedSchema}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Tables</span>
              <span className="font-medium">{selectedTables.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Mapped Fields</span>
              <span className="font-medium">{mappedFields.length}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Generated Fields</span>
              <span className="font-medium">{generatedFields.length}</span>
            </div>
          </div>
        </div>

        {/* Field Mappings */}
        <div className="bg-muted rounded-lg p-4">
          <h3 className="font-medium mb-3">Field Mappings</h3>
          <div className="space-y-2 text-sm">
            {fieldMappings.map((mapping) => (
              <div key={mapping.targetField} className="flex justify-between">
                <span className="text-muted-foreground capitalize">{mapping.targetField}</span>
                <span className="font-medium">
                  {mapping.sourceType === 'column'
                    ? mapping.sourceColumn
                    : 'AI Generated'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Success Message */}
      <div className="bg-success/20 border border-success/50 rounded-lg p-4 mb-8">
        <div className="flex items-start">
          <svg className="w-5 h-5 text-success mt-0.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h4 className="font-medium text-success">Configuration Ready</h4>
            <p className="text-sm mt-1">Your configuration will create the enriched table and be ready for analytics processing.</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-between">
        <button
          onClick={handleStartOver}
          disabled={saveConfig.isPending}
          className="px-6 py-2 border border-border rounded-md hover:bg-muted disabled:opacity-50"
        >
          Start Over
        </button>
        <button
          onClick={handleSave}
          disabled={saveConfig.isPending}
          className="
            bg-primary text-primary-foreground px-6 py-2 rounded-md
            hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {saveConfig.isPending ? 'Saving Configuration...' : 'Save & Continue'}
        </button>
      </div>
    </div>
  )
}
