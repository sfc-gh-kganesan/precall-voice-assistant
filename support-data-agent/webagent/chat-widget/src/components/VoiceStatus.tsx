/**
 * Voice Status Indicator
 */

import React from 'react';

interface VoiceStatusProps {
  status: string;
}

export const VoiceStatus: React.FC<VoiceStatusProps> = ({ status }) => {
  if (!status) return null;

  return (
    <div
      id="snowflake-voice-status"
      style={{
        padding: '8px 16px',
        backgroundColor: '#f5f5f5',
        borderTop: '1px solid #e0e0e0',
        fontSize: '14px',
        color: '#666',
        textAlign: 'center',
      }}
    >
      <span className="voice-status-text">{status}</span>
    </div>
  );
};
