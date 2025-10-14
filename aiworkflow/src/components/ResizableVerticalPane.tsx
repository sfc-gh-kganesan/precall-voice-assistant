import React, { useState, useRef, useEffect } from 'react'

interface ResizableVerticalPaneProps {
  children: React.ReactNode
  initialHeight?: number
  minHeight?: number
  maxHeight?: number
  className?: string
  onHeightChange?: (height: number) => void
}

export const ResizableVerticalPane: React.FC<ResizableVerticalPaneProps> = ({
  children,
  initialHeight = 200,
  minHeight = 100,
  maxHeight = 400,
  className = '',
  onHeightChange
}) => {
  const [height, setHeight] = useState(initialHeight)
  const [isResizing, setIsResizing] = useState(false)
  const paneRef = useRef<HTMLDivElement>(null)
  const startYRef = useRef(0)
  const startHeightRef = useRef(0)

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return

      const deltaY = startYRef.current - e.clientY // Inverted for vertical resize
      const newHeight = Math.max(minHeight, Math.min(maxHeight, startHeightRef.current + deltaY))
      setHeight(newHeight)
      if (onHeightChange) {
        onHeightChange(newHeight)
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.body.classList.remove('resizing-vertical')
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'row-resize'
      document.body.style.userSelect = 'none'
      document.body.classList.add('resizing-vertical')
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing, minHeight, maxHeight])

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    startYRef.current = e.clientY
    startHeightRef.current = height
  }

  return (
    <div
      ref={paneRef}
      className={`resizable-vertical-pane ${className}`}
      style={{ height: `${height}px` }}
    >
      <div
        className="resize-handle resize-handle-vertical-top"
        onMouseDown={handleMouseDown}
      />
      {children}
    </div>
  )
}
