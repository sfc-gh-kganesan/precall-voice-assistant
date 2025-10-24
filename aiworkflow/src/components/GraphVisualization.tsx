import React, { useState, useEffect } from 'react'
import { apiService } from '../services/api'

interface GraphNode {
  id: string
  title: string
  description: string
  type: 'start' | 'process' | 'decision' | 'end'
  position: { x: number; y: number }
}

interface GraphVisualizationProps {
  selectedFile?: string | null
}

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({ selectedFile }) => {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<Array<{ from: string; to: string }>>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadWorkflowGraph()
  }, [selectedFile])

  const loadWorkflowGraph = async () => {
    setIsLoading(true)
    try {
      const graphData = await apiService.getWorkflowGraph(selectedFile || undefined)
      console.log('Loaded graph data:', graphData) // Debug log
      setNodes(graphData.nodes)
      setEdges(graphData.edges || [])
      console.log('Edges to render:', graphData.edges || []) // Debug log
    } catch (error) {
      console.error('Failed to load workflow graph:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getNodeTypeColor = (type: string) => {
    switch (type) {
      case 'start': return '#4CAF50'
      case 'end': return '#F44336'
      case 'decision': return '#FF9800'
      case 'process':
      default: return '#2196F3'
    }
  }

  const getNodeTypeIcon = (type: string) => {
    switch (type) {
      case 'start': return '▶'
      case 'end': return '⏹'
      case 'decision': return '◆'
      case 'process':
      default: return '⬜'
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
        {selectedFile && (
          <div style={{
            fontSize: '11px',
            color: 'var(--text-muted)',
            fontWeight: 'normal',
            marginTop: '2px'
          }}>
            {selectedFile.split('/').pop()}
          </div>
        )}
      </h3>

      {nodes.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
          {selectedFile
            ? 'No LangGraph workflow detected in this file.'
            : 'Select a Python file to see workflow graph, or start coding to see the default graph!'
          }
        </div>
      ) : (
        <div style={{ position: 'relative', minHeight: '300px', padding: '10px' }}>
          {/* Render nodes */}
          {nodes.map(node => (
            <div
              key={node.id}
              className="graph-node"
              style={{
                position: 'absolute',
                left: `${node.position.x}px`,
                top: `${node.position.y}px`,
                background: 'var(--bg-secondary)',
                border: `2px solid ${getNodeTypeColor(node.type)}`,
                borderRadius: '8px',
                padding: '8px 12px',
                minWidth: '120px',
                fontSize: '11px',
                cursor: 'pointer',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                zIndex: 10 // Ensure nodes are on top
              }}
              title={node.description}
            >
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginBottom: '4px'
              }}>
                <span style={{ color: getNodeTypeColor(node.type) }}>
                  {getNodeTypeIcon(node.type)}
                </span>
                <div style={{
                  fontWeight: '600',
                  color: 'var(--text-primary)',
                  fontSize: '12px'
                }}>
                  {node.title}
                </div>
              </div>
              <div style={{
                color: 'var(--text-muted)',
                fontSize: '10px',
                lineHeight: '1.3'
              }}>
                {node.description}
              </div>
            </div>
          ))}

          {/* Render edges as simple lines */}
          <svg
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
              zIndex: 1 // Put above background but below nodes
            }}
          >
            {edges.map((edge, index) => {
              const fromNode = nodes.find(n => n.id === edge.from)
              const toNode = nodes.find(n => n.id === edge.to)

              if (!fromNode || !toNode) {
                console.warn(`Edge ${edge.from} -> ${edge.to}: missing node`, { fromNode, toNode })
                return null
              }

              const fromX = fromNode.position.x + 60 // Center of node (assuming 120px width)
              const fromY = fromNode.position.y + 25 // Center vertically
              const toX = toNode.position.x + 60
              const toY = toNode.position.y + 25

              console.log(`Rendering edge ${edge.from} -> ${edge.to}:`, { fromX, fromY, toX, toY })

              return (
                <g key={`${edge.from}-${edge.to}-${index}`}>
                  <line
                    x1={fromX}
                    y1={fromY}
                    x2={toX}
                    y2={toY}
                    stroke="var(--text-secondary)"
                    strokeWidth="2"
                    opacity="0.8"
                  />
                  {/* Arrow head */}
                  <polygon
                    points={`${toX-6},${toY-4} ${toX},${toY} ${toX-6},${toY+4}`}
                    fill="var(--text-secondary)"
                    opacity="0.8"
                  />
                </g>
              )
            })}
          </svg>
        </div>
      )}
    </div>
  )
}
