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

  // Workflow graph operations
  async getWorkflowGraph(): Promise<WorkflowGraph> {
    const response = await axios.get(`${API_BASE_URL}/workflow/graph`)
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
