import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { UploadCloud, FileText } from 'lucide-react';

export const UploadScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animation timings
  const browserScale = spring({
    frame,
    fps,
    config: { damping: 100, stiffness: 200 },
  });

  const dropzoneOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const fileAppear = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const uploadProgress = interpolate(frame, [90, 140], [0, 100], {
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
          opacity: interpolate(frame, [0, 20], [0, 1]),
        }}
      >
        <h2
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: '#f1f5f9',
            margin: 0,
            marginBottom: 16,
          }}
        >
          Upload Your Script
        </h2>
        <p
          style={{
            fontSize: 24,
            color: '#94a3b8',
            margin: 0,
          }}
        >
          Drag & drop your screenplay PDF
        </p>
      </div>

      {/* Browser Window Mockup */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: `translate(-50%, -50%) scale(${browserScale})`,
          width: 900,
          height: 500,
          backgroundColor: '#1e293b',
          borderRadius: 16,
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          overflow: 'hidden',
        }}
      >
        {/* Browser Chrome */}
        <div
          style={{
            height: 50,
            backgroundColor: '#334155',
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            borderBottom: '1px solid #475569',
          }}
        >
          <div style={{ display: 'flex', gap: 8 }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#ef4444' }} />
            <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#f59e0b' }} />
            <div style={{ width: 12, height: 12, borderRadius: '50%', backgroundColor: '#10b981' }} />
          </div>
          <div
            style={{
              marginLeft: 20,
              flex: 1,
              height: 32,
              backgroundColor: '#1e293b',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              padding: '0 12px',
              fontSize: 14,
              color: '#94a3b8',
            }}
          >
            www.slateone.studio/upload
          </div>
        </div>

        {/* Drop Zone */}
        <div
          style={{
            position: 'absolute',
            top: 120,
            left: 100,
            right: 100,
            height: 300,
            border: '3px dashed #475569',
            borderRadius: 12,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: dropzoneOpacity,
            backgroundColor: frame > 60 ? '#1e293b' : 'transparent',
            transition: 'background-color 0.3s',
          }}
        >
          {frame < 60 ? (
            <>
              <UploadCloud size={64} color="#94a3b8" />
              <p style={{ fontSize: 20, color: '#f1f5f9', marginTop: 20 }}>
                Drop your script here
              </p>
              <p style={{ fontSize: 16, color: '#64748b', marginTop: 8 }}>
                or click to browse
              </p>
            </>
          ) : (
            <>
              <div style={{ opacity: fileAppear }}>
                <FileText size={48} color="#fbbf24" />
                <p style={{ fontSize: 18, color: '#f1f5f9', marginTop: 12 }}>
                  screenplay.pdf
                </p>
              </div>

              {/* Upload Progress */}
              {frame > 90 && (
                <div
                  style={{
                    width: 400,
                    marginTop: 30,
                  }}
                >
                  <div
                    style={{
                      width: '100%',
                      height: 8,
                      backgroundColor: '#334155',
                      borderRadius: 4,
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        width: `${uploadProgress}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
                        borderRadius: 4,
                      }}
                    />
                  </div>
                  <p style={{ fontSize: 14, color: '#94a3b8', marginTop: 8, textAlign: 'center' }}>
                    {uploadProgress < 100 ? `Uploading... ${Math.round(uploadProgress)}%` : 'Upload complete!'}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
