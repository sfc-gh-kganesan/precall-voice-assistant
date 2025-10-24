import React, { useState, useEffect, useRef } from 'react'
import MonacoEditor from '@monaco-editor/react'
import { FileText, Sun, Moon } from 'lucide-react'
import { FileBrowser } from './components/FileBrowser'
import { GraphVisualization } from './components/GraphVisualization'
import { ChatInterface } from './components/ChatInterface'
import { ResizablePane } from './components/ResizablePane'
import { ResizableVerticalPane } from './components/ResizableVerticalPane'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import { apiService } from './services/api'

interface FileItem {
  name: string
  type: 'file' | 'folder'
  path: string
  children?: FileItem[]
}

const AppContent: React.FC = () => {
  const { theme, toggleTheme } = useTheme()
  const [files, setFiles] = useState<FileItem[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [workflowName, setWorkflowName] = useState<string>('Untitled Workflow')
  const [isLoading, setIsLoading] = useState(true)
  const [chatHeight, setChatHeight] = useState<number>(200)
  const [isRenaming, setIsRenaming] = useState(false)
  const [tempWorkflowName, setTempWorkflowName] = useState('')

  useEffect(() => {
    loadFiles()
  }, [])

  useEffect(() => {
    if (selectedFile) {
      loadFileContent(selectedFile)
    }
  }, [selectedFile])

  // Force Monaco Editor to recalculate height when chat height changes
  useEffect(() => {
    // Trigger a window resize event to make Monaco Editor recalculate
    window.dispatchEvent(new Event('resize'))
  }, [chatHeight])

  // Update max widths when window is resized
  useEffect(() => {
    const handleResize = () => {
      // Force re-render to update max widths
      window.dispatchEvent(new Event('resize'))
    }

    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const calculateEditorHeight = () => {
    const windowHeight = window.innerHeight
    const titleBarHeight = 40
    const availableHeight = windowHeight - titleBarHeight - chatHeight
    return `${availableHeight}px`
  }

  const loadFiles = async () => {
    try {
      const fileList = await apiService.getFiles()
      setFiles(fileList)
    } catch (error) {
      console.error('Failed to load files:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const loadFileContent = async (filePath: string) => {
    try {
      const content = await apiService.getFileContent(filePath)
      setFileContent(content)
    } catch (error) {
      console.error('Failed to load file content:', error)
    }
  }

  const handleFileSelect = (filePath: string) => {
    setSelectedFile(filePath)
  }

  const handleFileContentChange = (value: string | undefined) => {
    if (value !== undefined) {
      setFileContent(value)
      // In a real app, you'd want to debounce this and save to backend
    }
  }

  const handleFileOperation = async (operation: string, filePath: string, newName?: string) => {
    try {
      switch (operation) {
        case 'create':
          await apiService.createFile(filePath)
          break
        case 'delete':
          await apiService.deleteFile(filePath)
          break
        case 'rename':
          if (newName) {
            await apiService.renameFile(filePath, newName)
          }
          break
      }
      await loadFiles()
    } catch (error) {
      console.error(`Failed to ${operation} file:`, error)
    }
  }

  const handleWorkflowNameClick = () => {
    setIsRenaming(true)
    setTempWorkflowName(workflowName)
  }

  const handleWorkflowNameSubmit = async () => {
    if (tempWorkflowName.trim() && tempWorkflowName !== workflowName) {
      try {
        await apiService.renameWorkflow('default-workflow-id', tempWorkflowName.trim())
        setWorkflowName(tempWorkflowName.trim())
      } catch (error) {
        console.error('Failed to rename workflow:', error)
      }
    }
    setIsRenaming(false)
  }

  const handleWorkflowNameCancel = () => {
    setIsRenaming(false)
    setTempWorkflowName('')
  }

  const handleWorkflowNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleWorkflowNameSubmit()
    } else if (e.key === 'Escape') {
      handleWorkflowNameCancel()
    }
  }

  if (isLoading) {
    return (
      <div style={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#1e1e1e',
        color: '#d4d4d4'
      }}>
        Loading AI Workflow...
      </div>
    )
  }

  return (
    <div className="app" data-theme={theme}>
      <div className="title-bar">
        <div className="title-bar-left">
          <FileText size={16} />
          {isRenaming ? (
            <input
              type="text"
              value={tempWorkflowName}
              onChange={(e) => setTempWorkflowName(e.target.value)}
              onBlur={handleWorkflowNameSubmit}
              onKeyDown={handleWorkflowNameKeyDown}
              className="workflow-name-input"
              autoFocus
            />
          ) : (
            <span 
              className="workflow-name"
              onClick={handleWorkflowNameClick}
              title="Click to rename workflow"
            >
              {workflowName}
            </span>
          )}
        </div>
        <div className="title-bar-right">
          <button 
            className="theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
          >
            {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
            {theme === 'light' ? 'Dark' : 'Light'}
          </button>
        </div>
      </div>
      
      <div className="main-content">
        <ResizablePane
          initialWidth={250}
          minWidth={150}
          maxWidth={window.innerWidth * 0.8}
          direction="horizontal"
          className="sidebar"
        >
          <FileBrowser
            files={files}
            selectedFile={selectedFile}
            onFileSelect={handleFileSelect}
            onFileOperation={handleFileOperation}
          />
        </ResizablePane>
        
        <div className="content-area">
          <div className="editor-section">
            <div className="code-editor monaco-editor-container">
              <MonacoEditor
                height={calculateEditorHeight()}
                language="python"
                value={fileContent}
                onChange={handleFileContentChange}
                theme={theme === 'light' ? 'vs' : 'vs-dark'}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: 'on',
                  roundedSelection: false,
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  wordWrap: 'on',
                  wrappingIndent: 'indent',
                }}
              />
            </div>
            
            <ResizablePane
              initialWidth={300}
              minWidth={200}
              maxWidth={window.innerWidth * 0.6}
              direction="horizontal"
              className="graph-pane"
              resizeSide="left"
            >
              <GraphVisualization selectedFile={selectedFile} />
            </ResizablePane>
          </div>
          
          <ResizableVerticalPane
            initialHeight={200}
            minHeight={100}
            maxHeight={window.innerHeight * 0.8}
            className="chat-pane"
            onHeightChange={setChatHeight}
          >
            <ChatInterface />
          </ResizableVerticalPane>
        </div>
      </div>
    </div>
  )
}

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  )
}

export default App
