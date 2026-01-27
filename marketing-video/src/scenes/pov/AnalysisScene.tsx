import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { Sparkles, Loader } from 'lucide-react';

export const AnalysisScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const progressValue = interpolate(frame, [30, 130], [0, 100], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const sceneItems = [
    { number: '1', setting: 'INT. COFFEE SHOP - DAY', time: 30 },
    { number: '2', setting: 'EXT. CITY STREET - DAY', time: 50 },
    { number: '3', setting: 'INT. APARTMENT - NIGHT', time: 70 },
    { number: '4', setting: 'INT. OFFICE - DAY', time: 90 },
    { number: '5', setting: 'EXT. PARK - SUNSET', time: 110 },
  ];

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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
          <Sparkles size={40} color="#fbbf24" />
          <h2
            style={{
              fontSize: 48,
              fontWeight: 700,
              background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              margin: 0,
            }}
          >
            AI Analysis in Progress
          </h2>
        </div>
        <p
          style={{
            fontSize: 24,
            color: '#94a3b8',
            marginTop: 16,
          }}
        >
          Powered by Google Gemini 2.0
        </p>
      </div>

      {/* Analysis Progress */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 800,
        }}
      >
        {/* Progress Bar */}
        <div
          style={{
            width: '100%',
            height: 12,
            backgroundColor: '#1e293b',
            borderRadius: 6,
            overflow: 'hidden',
            marginBottom: 40,
          }}
        >
          <div
            style={{
              width: `${progressValue}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
              borderRadius: 6,
              boxShadow: '0 0 20px rgba(251, 191, 36, 0.5)',
            }}
          />
        </div>

        {/* Scene Detection List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {sceneItems.map((scene, index) => {
            const itemOpacity = interpolate(frame, [scene.time, scene.time + 15], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });

            const isAnalyzing = frame >= scene.time && frame < scene.time + 20;
            const isComplete = frame >= scene.time + 20;

            return (
              <div
                key={scene.number}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 16,
                  padding: '16px 24px',
                  backgroundColor: '#1e293b',
                  borderRadius: 8,
                  opacity: itemOpacity,
                  borderLeft: isComplete ? '4px solid #10b981' : '4px solid #475569',
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: '50%',
                    backgroundColor: isComplete ? '#10b981' : '#334155',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 18,
                    fontWeight: 700,
                    color: '#f1f5f9',
                  }}
                >
                  {isComplete ? '✓' : scene.number}
                </div>
                <div style={{ flex: 1 }}>
                  <p style={{ fontSize: 18, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                    Scene {scene.number}
                  </p>
                  <p style={{ fontSize: 14, color: '#94a3b8', margin: 0, marginTop: 4 }}>
                    {scene.setting}
                  </p>
                </div>
                {isAnalyzing && !isComplete && (
                  <Loader size={20} color="#fbbf24" style={{ animation: 'spin 1s linear infinite' }} />
                )}
              </div>
            );
          })}
        </div>

        {/* Status Text */}
        <p
          style={{
            textAlign: 'center',
            fontSize: 16,
            color: '#94a3b8',
            marginTop: 30,
          }}
        >
          {progressValue < 100 ? 'Detecting scenes and extracting metadata...' : 'Analysis complete! ✨'}
        </p>
      </div>
    </AbsoluteFill>
  );
};
