import { create } from 'zustand'
import { FieldMapping } from '@/types'

interface AdminState {
  currentStep: number
  selectedDatabase: string | null
  selectedSchema: string | null
  selectedTables: string[]
  fieldMappings: FieldMapping[]
  generationJobId: string | null

  configurationId: string | null
  configurationName: string
  outputTableName: string
  analyticsJobId: string | null
  setCurrentStep: (step: number) => void
  setSelectedDatabase: (database: string | null) => void
  setSelectedSchema: (schema: string | null) => void
  setSelectedTables: (tables: string[]) => void
  setFieldMappings: (mappings: FieldMapping[]) => void
  setGenerationJobId: (jobId: string | null) => void
  setConfigurationId: (configId: string | null) => void
  setConfigurationName: (name: string) => void
  setOutputTableName: (tableName: string) => void
  setAnalyticsJobId: (jobId: string | null) => void
  reset: () => void
}

const initialState = {
  currentStep: 0,
  selectedDatabase: null,
  selectedSchema: null,
  selectedTables: [],
  fieldMappings: [],
  generationJobId: null,
  configurationId: null,
  configurationName: '',
  outputTableName: '',
  analyticsJobId: null,
}

export const useAdminStore = create<AdminState>((set) => ({
  ...initialState,

  setCurrentStep: (step) => set({ currentStep: step }),
  setSelectedDatabase: (database) => set({ selectedDatabase: database }),
  setSelectedSchema: (schema) => set({ selectedSchema: schema }),
  setSelectedTables: (tables) => set({ selectedTables: tables }),
  setFieldMappings: (mappings) => set({ fieldMappings: mappings }),
  setGenerationJobId: (jobId) => set({ generationJobId: jobId }),
  setConfigurationId: (configId) => set({ configurationId: configId }),
  setConfigurationName: (name) => set({ configurationName: name }),
  setOutputTableName: (tableName) => set({ outputTableName: tableName }),
  setAnalyticsJobId: (jobId) => set({ analyticsJobId: jobId }),
  reset: () => set(initialState),
}))
