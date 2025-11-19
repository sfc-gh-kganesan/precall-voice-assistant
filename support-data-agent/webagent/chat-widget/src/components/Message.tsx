/**
 * Individual Message Component
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { Message as MessageType } from '../types';

interface MessageProps {
  message: MessageType;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isAgent = message.role === 'agent';

  // Format timestamp
  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (isAgent) {
    // Agent message - left aligned with metadata
    return (
      <div
        style={{
          maxWidth: '85%',
          alignSelf: 'flex-start',
          marginBottom: '16px',
        }}
      >
        <div
          className="chat-message agent"
          style={{
            backgroundColor: '#f5f5f5',
            color: '#333',
            padding: '12px 16px',
            borderRadius: '12px',
            wordWrap: 'break-word',
            border: '1px solid #e0e0e0',
          }}
        >
          <div className="message-content" style={{
            fontSize: '14px',
            lineHeight: '1.6',
          }}>
            <ReactMarkdown
              components={{
                // Paragraphs
                p: ({ children }) => (
                  <p style={{ margin: '0 0 8px 0', lineHeight: '1.6' }}>
                    {children}
                  </p>
                ),
                // Headings
                h1: ({ children }) => (
                  <h1 style={{ fontSize: '20px', fontWeight: 700, margin: '8px 0' }}>
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 style={{ fontSize: '18px', fontWeight: 700, margin: '8px 0' }}>
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '8px 0' }}>
                    {children}
                  </h3>
                ),
                // Lists
                ul: ({ children }) => (
                  <ul style={{ margin: '8px 0', paddingLeft: '20px', listStyleType: 'disc' }}>
                    {children}
                  </ul>
                ),
                ol: ({ children }) => (
                  <ol style={{ margin: '8px 0', paddingLeft: '20px' }}>
                    {children}
                  </ol>
                ),
                li: ({ children }) => (
                  <li style={{ margin: '4px 0' }}>
                    {children}
                  </li>
                ),
                // Code blocks
                code: ({ inline, className, children, ...props }: any) => {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={vscDarkPlus}
                      language={match[1]}
                      PreTag="div"
                      customStyle={{
                        margin: '8px 0',
                        borderRadius: '4px',
                        fontSize: '13px',
                      }}
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code
                      style={{
                        backgroundColor: '#e0e0e0',
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                        fontSize: '13px',
                      }}
                      {...props}
                    >
                      {children}
                    </code>
                  );
                },
                // Links
                a: ({ children, href }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: '#29b5e8',
                      textDecoration: 'underline',
                      fontWeight: 600,
                    }}
                  >
                    {children}
                  </a>
                ),
                // Blockquotes
                blockquote: ({ children }) => (
                  <blockquote
                    style={{
                      borderLeft: '3px solid #29b5e8',
                      paddingLeft: '12px',
                      margin: '8px 0',
                      fontStyle: 'italic',
                    }}
                  >
                    {children}
                  </blockquote>
                ),
                // Strong (bold)
                strong: ({ children }) => (
                  <strong style={{ fontWeight: 700 }}>
                    {children}
                  </strong>
                ),
                // Emphasis (italic)
                em: ({ children }) => (
                  <em style={{ fontStyle: 'italic' }}>
                    {children}
                  </em>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
        {/* Metadata */}
        <div
          style={{
            fontSize: '11px',
            color: '#999',
            marginTop: '4px',
            marginLeft: '4px',
          }}
        >
          Snowflake Assistant • {formatTime(message.timestamp)}
        </div>
      </div>
    );
  } else {
    // User message - right aligned, white bubble
    return (
      <div
        style={{
          maxWidth: '70%',
          alignSelf: 'flex-end',
          marginBottom: '16px',
        }}
      >
        {message.label && (
          <div
            style={{
              fontSize: '11px',
              color: '#999',
              marginBottom: '4px',
              textAlign: 'right',
              marginRight: '4px',
            }}
          >
            {message.label}
          </div>
        )}
        <div
          className="chat-message user"
          style={{
            backgroundColor: '#29b5e8',
            color: 'white',
            padding: '12px 16px',
            borderRadius: '18px',
            wordWrap: 'break-word',
            boxShadow: '0 2px 4px rgba(41, 181, 232, 0.2)',
          }}
        >
          <div className="message-content" style={{
            fontSize: '14px',
            lineHeight: '1.5',
          }}>
            {message.content}
          </div>
        </div>
      </div>
    );
  }
};
