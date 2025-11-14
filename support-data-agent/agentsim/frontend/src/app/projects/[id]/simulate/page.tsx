'use client'

import { use, useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Papa from 'papaparse'
import { projectsApi, simulationsApi } from '@/lib/api'
import type { Project, SimulationCreate, CustomScenario, Persona, PersonaTemplate } from '@/lib/types'

export default function SimulatePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const projectId = parseInt(id)
  const [project, setProject] = useState<Project | null>(null)
  const [savedPersonas, setSavedPersonas] = useState<PersonaTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [customPersonas, setCustomPersonas] = useState<CustomScenario[]>([])
  const [showPersonaForm, setShowPersonaForm] = useState(false)
  const [selectedSavedPersonas, setSelectedSavedPersonas] = useState<number[]>([])
  const [savePersona, setSavePersona] = useState(false)
  const [knowledgeBaseJson, setKnowledgeBaseJson] = useState('')
  const [showImportModal, setShowImportModal] = useState(false)
  const [importedPersonas, setImportedPersonas] = useState<CustomScenario[]>([])
  const [importWarnings, setImportWarnings] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [formData, setFormData] = useState<SimulationCreate>({
    project_id: projectId,
    num_simulations: 3,
    concurrency: 2,
    max_turns: 20,
    timeout_seconds: 120,
    conversation_timeout_seconds: 600,
    stop_conditions: ['max_turns', 'agent_signal'],
    metrics_config: ['efficiency', 'quality', 'tool_usage'],
    edge_case_ratio: 0.2,
    custom_scenarios: [],
  })

  const [newPersona, setNewPersona] = useState<CustomScenario>({
    persona: {
      name: '',
      goal: '',
      tone: 'professional',
      personality_traits: [],
      technical_level: 'intermediate',
      edge_case: false,
    },
    initial_query: '',
    expected_outcome: '',
    complexity: 'simple',
    category: 'general',
  })

  useEffect(() => {
    loadProject()
    loadSavedPersonas()
  }, [])

  const loadProject = async () => {
    try {
      const response = await projectsApi.get(projectId)
      setProject(response.data)
    } catch (error) {
      console.error('Failed to load project:', error)
    }
  }

  const loadSavedPersonas = async () => {
    try {
      const response = await projectsApi.getPersonas(projectId)
      setSavedPersonas(response.data)
    } catch (error) {
      console.error('Failed to load saved personas:', error)
    }
  }

  const toggleSavedPersona = (personaId: number) => {
    setSelectedSavedPersonas(prev =>
      prev.includes(personaId)
        ? prev.filter(id => id !== personaId)
        : [...prev, personaId]
    )
  }

  const addPersona = async () => {
    if (!newPersona.persona.name || !newPersona.initial_query) {
      alert('Please fill in persona name and initial query')
      return
    }

    // Parse knowledge base JSON if provided
    let knowledgeBase = undefined
    if (knowledgeBaseJson.trim()) {
      try {
        knowledgeBase = JSON.parse(knowledgeBaseJson)
      } catch (error) {
        alert('Invalid JSON in knowledge base. Please check your syntax.')
        return
      }
    }

    // Save persona to database if requested
    if (savePersona) {
      try {
        const response = await projectsApi.createPersona(projectId, {
          name: newPersona.persona.name,
          goal: newPersona.persona.goal,
          tone: newPersona.persona.tone,
          personality_traits: newPersona.persona.personality_traits,
          technical_level: newPersona.persona.technical_level,
          edge_case: newPersona.persona.edge_case,
          default_query: newPersona.initial_query,
          expected_outcome: newPersona.expected_outcome,
          complexity: newPersona.complexity,
          category: newPersona.category,
          knowledge_base: knowledgeBase,
        })

        // Reload saved personas
        await loadSavedPersonas()

        // Auto-select the newly saved persona
        setSelectedSavedPersonas([...selectedSavedPersonas, response.data.id])
      } catch (error) {
        console.error('Failed to save persona:', error)
        alert('Failed to save persona for later use')
        return
      }
    } else {
      // Only add to custom personas if NOT saving for later
      setCustomPersonas([...customPersonas, newPersona])
    }

    // Reset form
    setNewPersona({
      persona: {
        name: '',
        goal: '',
        tone: 'professional',
        personality_traits: [],
        technical_level: 'intermediate',
        edge_case: false,
      },
      initial_query: '',
      expected_outcome: '',
      complexity: 'simple',
      category: 'general',
    })
    setKnowledgeBaseJson('')
    setSavePersona(false)
    setShowPersonaForm(false)
  }

  const removePersona = (index: number) => {
    setCustomPersonas(customPersonas.filter((_, i) => i !== index))
  }

  const handleFileImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const warnings: string[] = []
    const reader = new FileReader()

    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        let parsedData: any[] = []

        // Parse based on file extension
        if (file.name.endsWith('.json')) {
          parsedData = JSON.parse(content)
          if (!Array.isArray(parsedData)) {
            alert('JSON file must contain an array of personas')
            return
          }
        } else if (file.name.endsWith('.csv')) {
          const result = Papa.parse(content, { header: true, skipEmptyLines: true })
          parsedData = result.data as any[]
        } else {
          alert('Please upload a .csv or .json file')
          return
        }

        // Fuzzy column mapping
        const mapColumn = (row: any, possibleNames: string[]): string => {
          for (const name of possibleNames) {
            const key = Object.keys(row).find(k => k.toLowerCase().trim() === name.toLowerCase())
            if (key && row[key]) return row[key]
          }
          return ''
        }

        // Convert to CustomScenario format
        const personas: CustomScenario[] = []
        for (let i = 0; i < parsedData.length; i++) {
          const row = parsedData[i]

          const name = mapColumn(row, ['name', 'persona_name', 'persona'])
          if (!name) {
            warnings.push(`Row ${i + 1}: Missing required 'name' field, skipping`)
            continue
          }

          const goal = mapColumn(row, ['goal', 'objective', 'purpose'])
          const initial_query = mapColumn(row, ['initial_query', 'query', 'default_query'])

          if (!initial_query) {
            warnings.push(`Row ${i + 1} (${name}): Missing 'initial_query', using default`)
          }

          // Parse knowledge_base if it's a string
          let knowledge_base: any = undefined
          const kbStr = mapColumn(row, ['knowledge_base', 'knowledge'])
          if (kbStr) {
            try {
              knowledge_base = JSON.parse(kbStr)
            } catch {
              warnings.push(`Row ${i + 1} (${name}): Invalid JSON in knowledge_base, will be empty`)
            }
          }

          // Parse personality_traits if it's a string
          let personality_traits: string[] = []
          const traitsStr = mapColumn(row, ['personality_traits', 'traits', 'personality'])
          if (traitsStr) {
            personality_traits = traitsStr.split(',').map(t => t.trim()).filter(t => t)
          }

          personas.push({
            persona: {
              name,
              goal: goal || '',
              tone: mapColumn(row, ['tone', 'attitude', 'mood']) || 'professional',
              personality_traits,
              technical_level: mapColumn(row, ['technical_level', 'tech_level', 'skill_level', 'expertise']) || 'intermediate',
              edge_case: mapColumn(row, ['edge_case']).toLowerCase() === 'true',
              knowledge_base,  // Include parsed knowledge_base from CSV
            },
            initial_query: initial_query || 'Help me with my issue',
            expected_outcome: mapColumn(row, ['expected_outcome', 'outcome']),
            complexity: mapColumn(row, ['complexity']) || 'simple',
            category: mapColumn(row, ['category']) || 'general',
            knowledge_base,  // Also include at scenario level for backend access
          })
        }

        setImportedPersonas(personas)
        setImportWarnings(warnings)
        setShowImportModal(true)
      } catch (error) {
        alert(`Failed to parse file: ${error}`)
      }
    }

    reader.readAsText(file)
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const confirmImport = () => {
    setCustomPersonas([...customPersonas, ...importedPersonas])
    setShowImportModal(false)
    setImportedPersonas([])
    setImportWarnings([])
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Convert selected saved personas to custom scenarios
      const savedPersonaScenarios: CustomScenario[] = savedPersonas
        .filter(p => selectedSavedPersonas.includes(p.id))
        .map(p => ({
          persona: {
            name: p.name,
            goal: p.goal,
            tone: p.tone,
            personality_traits: p.personality_traits,
            technical_level: p.technical_level,
            edge_case: p.edge_case,
          },
          initial_query: p.default_query || '',
          expected_outcome: p.expected_outcome || '',
          complexity: p.complexity,
          category: p.category,
        }))

      const allScenarios = [...savedPersonaScenarios, ...customPersonas]

      const simulationData = {
        ...formData,
        custom_scenarios: allScenarios.length > 0 ? allScenarios : undefined,
        num_simulations: formData.num_simulations,
      }

      const response = await simulationsApi.create(simulationData)
      router.push(`/simulations/${response.data.id}`)
    } catch (error) {
      alert('Failed to create simulation')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  if (!project) {
    return <div className="p-8 text-center text-parchment-200">Loading...</div>
  }

  const totalPersonas = selectedSavedPersonas.length + customPersonas.length

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-serif font-bold text-parchment-100">Run Simulation</h1>
        <p className="mt-2 text-sm text-parchment-200">
          Testing: {project.name}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Basic Configuration */}
        <div className="bg-slate-900 shadow-sm rounded-lg border border-slate-700 p-6">
          <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-4">Configuration</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-parchment-200">
                Number of Simulations
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={formData.num_simulations}
                onChange={(e) => setFormData({...formData, num_simulations: parseInt(e.target.value) || 1})}
                className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />
              {totalPersonas > 0 && (
                <p className="mt-1 text-xs text-parchment-300">{totalPersonas} personas selected (will be distributed across simulations)</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-parchment-200">
                Concurrency
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={formData.concurrency}
                onChange={(e) => setFormData({...formData, concurrency: parseInt(e.target.value) || 1})}
                className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-parchment-200">
                Max Turns per Conversation
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={formData.max_turns}
                onChange={(e) => setFormData({...formData, max_turns: parseInt(e.target.value) || 1})}
                className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-parchment-200">
                Timeout (seconds)
              </label>
              <input
                type="number"
                min="30"
                max="600"
                value={formData.timeout_seconds}
                onChange={(e) => setFormData({...formData, timeout_seconds: parseInt(e.target.value) || 30})}
                className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />
              <p className="mt-1 text-xs text-parchment-300">Timeout for stop conditions evaluation</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-parchment-200">
                Conversation Timeout (seconds)
              </label>
              <input
                type="number"
                min="60"
                max="1800"
                value={formData.conversation_timeout_seconds}
                onChange={(e) => setFormData({...formData, conversation_timeout_seconds: parseInt(e.target.value) || 600})}
                className="mt-1 block w-full rounded-md border border-slate-700 bg-slate-800 text-parchment-100 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />
              <p className="mt-1 text-xs text-parchment-300">Maximum time per conversation before timeout (default: 600s / 10 minutes)</p>
            </div>
          </div>
        </div>

        {/* Saved Personas */}
        {savedPersonas.length > 0 && (
          <div className="bg-slate-900 shadow-sm rounded-lg border border-slate-700 p-6">
            <h2 className="text-lg font-serif font-semibold text-parchment-100 mb-4">Saved Personas</h2>
            <p className="text-sm text-parchment-200 mb-4">Select personas to use in this simulation</p>

            <div className="space-y-2">
              {savedPersonas.map((persona) => (
                <label
                  key={persona.id}
                  className={`flex items-start p-3 rounded-md cursor-pointer transition-colors ${
                    selectedSavedPersonas.includes(persona.id)
                      ? 'bg-strategic-600/20 border border-strategic-600'
                      : 'bg-slate-800 border border-slate-700 hover:border-slate-600'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedSavedPersonas.includes(persona.id)}
                    onChange={() => toggleSavedPersona(persona.id)}
                    className="mt-1 mr-3"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm text-parchment-100">{persona.name}</div>
                    <div className="text-xs text-parchment-200 mt-1">{persona.goal}</div>
                    {persona.default_query && (
                      <div className="text-xs text-parchment-300 mt-1 italic">
                        &quot;{persona.default_query}&quot;
                      </div>
                    )}
                    <div className="text-xs text-parchment-300 mt-1">
                      {persona.tone} • {persona.technical_level} • {persona.complexity}
                      {persona.knowledge_base && ' • Has knowledge base'}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        {/* Custom Personas */}
        <div className="bg-slate-900 shadow-sm rounded-lg border border-slate-700 p-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-lg font-serif font-semibold text-parchment-100">Create New Persona</h2>
              <p className="text-xs text-parchment-300 mt-1">Create personas for one-time use or save for future simulations</p>
            </div>
            <div className="flex gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json"
                onChange={handleFileImport}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-1 text-sm font-medium text-parchment-200 border border-slate-600 rounded-md hover:bg-slate-800 transition-colors"
              >
                📁 Import from File
              </button>
              <button
                type="button"
                onClick={() => setShowPersonaForm(!showPersonaForm)}
                className="px-3 py-1 text-sm font-medium text-strategic-600 border border-strategic-600 rounded-md hover:bg-strategic-600/10 transition-colors"
              >
                {showPersonaForm ? 'Cancel' : '+ Add Persona'}
              </button>
            </div>
          </div>

          {showPersonaForm && (
            <div className="mb-4 p-4 bg-slate-800 rounded-md space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Persona Name *"
                  value={newPersona.persona.name}
                  onChange={(e) => setNewPersona({
                    ...newPersona,
                    persona: {...newPersona.persona, name: e.target.value}
                  })}
                  className="rounded-md border border-slate-700 bg-slate-900 text-parchment-100 placeholder-parchment-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
                />
                <input
                  type="text"
                  placeholder="Goal"
                  value={newPersona.persona.goal}
                  onChange={(e) => setNewPersona({
                    ...newPersona,
                    persona: {...newPersona.persona, goal: e.target.value}
                  })}
                  className="rounded-md border border-slate-700 bg-slate-900 text-parchment-100 placeholder-parchment-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
                />
              </div>

              <textarea
                placeholder="Initial Query *"
                value={newPersona.initial_query}
                onChange={(e) => setNewPersona({...newPersona, initial_query: e.target.value})}
                rows={2}
                className="w-full rounded-md border border-slate-700 bg-slate-900 text-parchment-100 placeholder-parchment-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
              />

              <div className="grid grid-cols-3 gap-3">
                <select
                  value={newPersona.persona.tone}
                  onChange={(e) => setNewPersona({
                    ...newPersona,
                    persona: {...newPersona.persona, tone: e.target.value}
                  })}
                  className="rounded-md border border-slate-700 bg-slate-900 text-parchment-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
                >
                  <option value="professional">Professional</option>
                  <option value="casual">Casual</option>
                  <option value="urgent">Urgent</option>
                  <option value="frustrated">Frustrated</option>
                </select>

                <select
                  value={newPersona.persona.technical_level}
                  onChange={(e) => setNewPersona({
                    ...newPersona,
                    persona: {...newPersona.persona, technical_level: e.target.value}
                  })}
                  className="rounded-md border border-slate-700 bg-slate-900 text-parchment-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="expert">Expert</option>
                </select>

                <select
                  value={newPersona.complexity}
                  onChange={(e) => setNewPersona({...newPersona, complexity: e.target.value})}
                  className="rounded-md border border-slate-700 bg-slate-900 text-parchment-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-strategic-600"
                >
                  <option value="simple">Simple</option>
                  <option value="moderate">Moderate</option>
                  <option value="complex">Complex</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-parchment-200 mb-2">
                  Knowledge Base (Optional JSON)
                </label>
                <p className="text-xs text-parchment-300 mb-2">
                  Provide real data the persona can reference during the conversation (e.g., account numbers, query IDs, warehouse names)
                </p>
                <textarea
                  placeholder='{"account_locator": "EXAMPLE-ORG", "warehouse": "COMPUTE_WH", "query_id": "01234567"}'
                  value={knowledgeBaseJson}
                  onChange={(e) => setKnowledgeBaseJson(e.target.value)}
                  rows={4}
                  className="w-full rounded-md border border-slate-700 bg-slate-900 text-parchment-100 placeholder-parchment-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-strategic-600"
                />
              </div>

              <label className="flex items-center space-x-2 text-sm text-parchment-200">
                <input
                  type="checkbox"
                  checked={savePersona}
                  onChange={(e) => setSavePersona(e.target.checked)}
                  className="rounded"
                />
                <span>Save this persona for future simulations</span>
              </label>

              <button
                type="button"
                onClick={addPersona}
                className="w-full px-3 py-2 text-sm font-medium text-parchment-50 bg-strategic-600 rounded-md hover:bg-strategic-500 transition-colors"
              >
                Add Persona
              </button>
            </div>
          )}

          {customPersonas.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-parchment-200 mb-2">One-time personas (not saved):</p>
              {customPersonas.map((persona, index) => (
                <div key={index} className="flex justify-between items-start p-3 bg-slate-800 rounded-md">
                  <div className="flex-1">
                    <div className="font-medium text-sm text-parchment-100">{persona.persona.name}</div>
                    <div className="text-xs text-parchment-200 mt-1">{persona.initial_query}</div>
                    <div className="text-xs text-parchment-300 mt-1">
                      {persona.persona.tone} • {persona.persona.technical_level} • {persona.complexity}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => removePersona(index)}
                    className="text-red-400 hover:text-red-300 text-sm transition-colors"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <button
            type="button"
            onClick={() => router.push('/projects')}
            className="px-4 py-2 text-sm font-medium text-parchment-200 bg-slate-800 border border-slate-700 rounded-md hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 text-sm font-medium text-parchment-50 bg-green-700 rounded-md hover:bg-green-600 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Starting Simulation...' : 'Start Simulation'}
          </button>
        </div>
      </form>

      {/* Import Preview Modal */}
      {showImportModal && (
        <div
          className="fixed inset-0 bg-slate-900/80 backdrop-blur-sm overflow-y-auto z-50 flex items-center justify-center p-4"
          onClick={() => setShowImportModal(false)}
        >
          <div
            className="relative w-full max-w-2xl bg-slate-800 rounded-lg shadow-2xl border border-slate-700"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <h2 className="text-xl font-serif font-semibold text-parchment-100 mb-4">Import Personas</h2>

              <div className="mb-4">
                <p className="text-sm text-parchment-200">
                  ✓ Successfully parsed {importedPersonas.length} persona{importedPersonas.length !== 1 ? 's' : ''}
                </p>
              </div>

              {importWarnings.length > 0 && (
                <div className="mb-4 p-3 bg-yellow-900/20 border border-yellow-700 rounded-md">
                  <p className="text-sm font-medium text-yellow-300 mb-2">⚠️ Warnings:</p>
                  <ul className="text-xs text-yellow-200 space-y-1">
                    {importWarnings.map((warning, i) => (
                      <li key={i}>• {warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mb-4 max-h-64 overflow-y-auto space-y-2">
                <p className="text-sm font-medium text-parchment-200 mb-2">Preview:</p>
                {importedPersonas.map((persona, i) => (
                  <div key={i} className="p-3 bg-slate-900 rounded border border-slate-700">
                    <div className="font-medium text-sm text-parchment-100">{persona.persona.name}</div>
                    <div className="text-xs text-parchment-200 mt-1">{persona.initial_query}</div>
                    <div className="text-xs text-parchment-300 mt-1">
                      {persona.persona.tone} • {persona.persona.technical_level} • {persona.complexity}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowImportModal(false)}
                  className="px-4 py-2 text-sm font-medium text-parchment-200 bg-slate-700 rounded-md hover:bg-slate-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmImport}
                  className="px-4 py-2 text-sm font-medium text-parchment-50 bg-strategic-600 rounded-md hover:bg-strategic-500 transition-colors"
                >
                  Import All ({importedPersonas.length})
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
