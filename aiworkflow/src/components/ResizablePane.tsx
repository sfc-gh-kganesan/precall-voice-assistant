import React, { useState, useRef, useEffect } from 'react'

interface ResizablePaneProps {
  children: React.ReactNode
  initialWidth?: number
  minWidth?: number
  maxWidth?: number
  direction: 'horizontal' | 'vertical'
  className?: string
  resizeSide?: 'left' | 'right'
}

export const ResizablePane: React.FC<ResizablePaneProps> = ({
  children,
  initialWidth = 250,
  minWidth = 150,
  maxWidth = 500,
  direction,
  className = '',
  resizeSide = 'right'
}) => {
  const [width, setWidth] = useState(initialWidth)
  const [isResizing, setIsResizing] = useState(false)
  const paneRef = useRef<HTMLDivElement>(null)
  const startXRef = useRef(0)
  const startWidthRef = useRef(0)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return

      const deltaX = e.clientX - startXRef.current
      let adjustedDelta = deltaX
      
      if (resizeSide === 'left') {
        // When resizing from left edge, dragging left (negative delta) should increase width
        // and dragging right (positive delta) should decrease width
        adjustedDelta = -deltaX
      }
      
      const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + adjustedDelta))
      setWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.body.classList.remove('resizing')
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.body.classList.add('resizing')
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing, minWidth, maxWidth])

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    startXRef.current = e.clientX
    startWidthRef.current = width
  }

  const resizeHandleClass = direction === 'horizontal' ? 'resize-handle-horizontal' : 'resize-handle-vertical'

  return (
    <div
      ref={paneRef}
      className={`resizable-pane ${className}`}
      style={{ width: `${width}px` }}
    >
      {children}
      <div
        className={`resize-handle ${resizeHandleClass}`}
        onMouseDown={handleMouseDown}
        style={{
          position: 'absolute',
          backgroundColor: 'transparent',
          zIndex: 10,
          transition: 'background-color 0.1s',
          ...(direction === 'horizontal' ? {
            top: 0,
            [resizeSide]: -3,
            width: 6,
            height: '100%',
            cursor: 'col-resize'
          } : {
            bottom: -3,
            left: 0,
            right: 0,
            height: 6,
            cursor: 'row-resize'
          })
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#007acc'
          e.currentTarget.style.opacity = '0.3'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
          e.currentTarget.style.opacity = '1'
        }}
      />
    </div>
  )
}
