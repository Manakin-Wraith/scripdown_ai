import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { FileText, Download, CheckCircle } from 'lucide-react';

export const ExportScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const exportOptions = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const downloadProgress = interpolate(frame, [60, 100], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 100,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
        }}
      >
        <h2
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: '#f1f5f9',
            margin: 0,
          }}
        >
          Professional Exports
        </h2>
        <p style={{ fontSize: 24, color: '#94a3b8', marginTop: 16 }}>
          Share with your team, instantly
        </p>
      </div>

      {/* Export Options */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 700,
          opacity: exportOptions,
        }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 40 }}>
          {[
            { format: 'PDF', icon: '📄', desc: 'Full breakdown report' },
            { format: 'Excel', icon: '📊', desc: 'Spreadsheet format' },
            { format: 'CSV', icon: '📋', desc: 'Raw data export' },
            { format: 'JSON', icon: '{ }', desc: 'API integration' },
          ].map((option, index) => {
            const cardOpacity = interpolate(
              frame,
              [30 + index * 10, 50 + index * 10],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={option.format}
                style={{
                  padding: 24,
                  backgroundColor: '#1e293b',
                  borderRadius: 12,
                  border: '2px solid #334155',
                  opacity: cardOpacity,
                  cursor: 'pointer',
                  transition: 'all 0.3s',
                }}
              >
                <div style={{ fontSize: 40, marginBottom: 12 }}>{option.icon}</div>
                <h3 style={{ fontSize: 20, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  {option.format}
                </h3>
                <p style={{ fontSize: 14, color: '#94a3b8', margin: 0, marginTop: 6 }}>
                  {option.desc}
                </p>
              </div>
            );
          })}
        </div>

        {/* Download Progress */}
        {frame > 60 && (
          <div
            style={{
              padding: 24,
              backgroundColor: '#1e293b',
              borderRadius: 12,
              border: '2px solid #fbbf24',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
              <Download size={24} color="#fbbf24" />
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: 16, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  {downloadProgress < 100 ? 'Generating PDF...' : 'Download Complete!'}
                </p>
                <p style={{ fontSize: 13, color: '#94a3b8', margin: 0, marginTop: 4 }}>
                  screenplay_breakdown.pdf
                </p>
              </div>
              {downloadProgress >= 100 && (
                <CheckCircle size={24} color="#10b981" />
              )}
            </div>

            <div
              style={{
                width: '100%',
                height: 8,
                backgroundColor: '#0f172a',
                borderRadius: 4,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${downloadProgress}%`,
                  height: '100%',
                  background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
                  borderRadius: 4,
                }}
              />
            </div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
