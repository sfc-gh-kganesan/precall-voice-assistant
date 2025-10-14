import React, { useState, useEffect } from 'react'
import { apiService } from '../services/api'

interface GraphNode {
  id: string
  title: string
  description: string
  type: 'start' | 'process' | 'decision' | 'end'
  position: { x: number; y: number }
}

export const GraphVisualization: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadWorkflowGraph()
  }, [])

  const loadWorkflowGraph = async () => {
    try {
      const graphData = await apiService.getWorkflowGraph()
      setNodes(graphData.nodes)
    } catch (error) {
      console.error('Failed to load workflow graph:', error)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="graph-visualization">
        <h3 style={{ 
          fontSize: '14px', 
          fontWeight: '500', 
          marginBottom: '12px',
          color: 'var(--text-secondary)'
        }}>
          Workflow Graph
        </h3>
        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading...</div>
      </div>
    )
  }

  return (
    <div className="graph-visualization">
      <h3 style={{ 
        fontSize: '14px', 
        fontWeight: '500', 
        marginBottom: '12px',
        color: 'var(--text-secondary)'
      }}>
        Workflow Graph
      </h3>
      
      {nodes.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
          No workflow nodes found. Start coding to see the graph!
        </div>
      ) : (
        <div>
          {nodes.map(node => (
            <div key={node.id} className="graph-node">
              <div className="graph-node-title">{node.title}</div>
              <div className="graph-node-description">{node.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
