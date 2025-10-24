import axios from 'axios'

const API_BASE_URL = '/api'

interface FileItem {
  name: string
  type: 'file' | 'folder'
  path: string
  children?: FileItem[]
}

interface GraphNode {
  id: string
  title: string
  description: string
  type: 'start' | 'process' | 'decision' | 'end'
  position: { x: number; y: number }
}

interface WorkflowGraph {
  nodes: GraphNode[]
  edges: Array<{ from: string; to: string }>
}

export const apiService = {
  // File operations
  async getFiles(): Promise<FileItem[]> {
    const response = await axios.get(`${API_BASE_URL}/files`)
    return response.data
  },

  async getFileContent(filePath: string): Promise<string> {
    const response = await axios.get(`${API_BASE_URL}/files/content`, {
      params: { path: filePath }
    })
    return response.data.content
  },

  async createFile(filePath: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/files`, { path: filePath })
  },

  async deleteFile(filePath: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/files`, {
      params: { path: filePath }
    })
  },

  async renameFile(oldPath: string, newName: string): Promise<void> {
    await axios.put(`${API_BASE_URL}/files/rename`, {
      oldPath,
      newName
    })
  },

  async writeFileContent(filePath: string, content: string): Promise<void> {
    await axios.put(`${API_BASE_URL}/files/content`, {
      path: filePath,
      content
    })
  },

  // Chat operations
  async sendChatMessage(message: string): Promise<string> {
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      message
    })
    return response.data.response
  },

  async streamChatMessage(message: string, onChunk: (chunk: string) => void, onComplete: () => void): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body reader available')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                onChunk(data.content)
              }
              if (data.done) {
                onComplete()
                return
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e)
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },

  // Workflow graph operations
  async getWorkflowGraph(filePath?: string): Promise<WorkflowGraph> {
    const params = filePath ? { path: filePath } : {}
    const response = await axios.get(`${API_BASE_URL}/workflow/graph`, { params })
    return response.data
  },

  // Workflow operations
  async renameWorkflow(workflowId: string, newName: string): Promise<void> {
    await axios.put(`${API_BASE_URL}/workflow/rename`, {
      workflowId,
      newName
    })
  }
}
