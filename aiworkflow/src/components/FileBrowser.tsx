import React, { useState } from 'react'
import { FileText, Folder, Plus, Trash2, Edit3 } from 'lucide-react'

interface FileItem {
  name: string
  type: 'file' | 'folder'
  path: string
  children?: FileItem[]
}

interface FileBrowserProps {
  files: FileItem[]
  selectedFile: string | null
  onFileSelect: (filePath: string) => void
  onFileOperation: (operation: string, filePath: string, newName?: string) => void
}

export const FileBrowser: React.FC<FileBrowserProps> = ({
  files,
  selectedFile,
  onFileSelect,
  onFileOperation
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [editingFile, setEditingFile] = useState<string | null>(null)
  const [newFileName, setNewFileName] = useState('')

  const toggleFolder = (folderPath: string) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderPath)) {
      newExpanded.delete(folderPath)
    } else {
      newExpanded.add(folderPath)
    }
    setExpandedFolders(newExpanded)
  }

  const handleRename = (filePath: string) => {
    setEditingFile(filePath)
    setNewFileName(filePath.split('/').pop() || '')
  }

  const confirmRename = () => {
    if (editingFile && newFileName) {
      onFileOperation('rename', editingFile, newFileName)
    }
    setEditingFile(null)
    setNewFileName('')
  }

  const cancelRename = () => {
    setEditingFile(null)
    setNewFileName('')
  }

  const renderFileItem = (file: FileItem, depth: number = 0) => {
    const isExpanded = expandedFolders.has(file.path)
    const isSelected = selectedFile === file.path
    const isEditing = editingFile === file.path

    return (
      <div key={file.path}>
        <div
          className={`file-item ${isSelected ? 'active' : ''}`}
          style={{ paddingLeft: `${8 + depth * 16}px` }}
          onClick={() => {
            if (file.type === 'folder') {
              toggleFolder(file.path)
            } else {
              onFileSelect(file.path)
            }
          }}
        >
          {file.type === 'folder' ? (
            <Folder size={14} />
          ) : (
            <FileText size={14} />
          )}
          
          {isEditing ? (
            <input
              type="text"
              value={newFileName}
              onChange={(e) => setNewFileName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') confirmRename()
                if (e.key === 'Escape') cancelRename()
              }}
              onBlur={confirmRename}
              autoFocus
              style={{
                background: 'transparent',
                border: '1px solid var(--border-focus)',
                borderRadius: '2px',
                padding: '2px 4px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                flex: 1
              }}
            />
          ) : (
            <span>{file.name}</span>
          )}
          
          {!isEditing && (
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '4px' }}>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleRename(file.path)
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '2px'
                }}
              >
                <Edit3 size={12} />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onFileOperation('delete', file.path)
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: '2px'
                }}
              >
                <Trash2 size={12} />
              </button>
            </div>
          )}
        </div>
        
        {file.type === 'folder' && isExpanded && file.children && (
          <div>
            {file.children.map(child => renderFileItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="file-browser">
      <div style={{ 
        padding: '8px', 
        borderBottom: '1px solid #3e3e42',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <button
          onClick={() => onFileOperation('create', 'new_file.py')}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '4px',
            borderRadius: '3px'
          }}
        >
          <Plus size={14} />
        </button>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Files</span>
      </div>
      
      <div style={{ padding: '8px 0' }}>
        {files.map(file => renderFileItem(file))}
      </div>
    </div>
  )
}
