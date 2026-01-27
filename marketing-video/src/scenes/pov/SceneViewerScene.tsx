import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { Users, MapPin, Clock, Tag } from 'lucide-react';

export const SceneViewerScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 20], [0, 1]);
  const sidebarSlide = interpolate(frame, [20, 50], [-300, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const detailFade = interpolate(frame, [50, 80], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const highlightScene = interpolate(frame, [100, 120], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a' }}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 60,
          left: 0,
          right: 0,
          textAlign: 'center',
          opacity: titleOpacity,
        }}
      >
        <h2
          style={{
            fontSize: 42,
            fontWeight: 700,
            color: '#f1f5f9',
            margin: 0,
          }}
        >
          Intelligent Scene Breakdown
        </h2>
        <p style={{ fontSize: 20, color: '#94a3b8', marginTop: 12 }}>
          Every detail, automatically extracted
        </p>
      </div>

      {/* Interface Mockup */}
      <div
        style={{
          position: 'absolute',
          top: 180,
          left: 100,
          right: 100,
          bottom: 100,
          display: 'flex',
          gap: 20,
        }}
      >
        {/* Sidebar - Scene List */}
        <div
          style={{
            width: 300,
            backgroundColor: '#1e293b',
            borderRadius: 12,
            padding: 20,
            transform: `translateX(${sidebarSlide}px)`,
          }}
        >
          <h3 style={{ fontSize: 18, color: '#f1f5f9', marginBottom: 16, fontWeight: 600 }}>
            Scenes
          </h3>
          {[1, 2, 3, 4, 5].map((num) => (
            <div
              key={num}
              style={{
                padding: '12px 16px',
                backgroundColor: num === 2 ? '#334155' : 'transparent',
                borderRadius: 8,
                marginBottom: 8,
                borderLeft: num === 2 ? '3px solid #fbbf24' : '3px solid transparent',
              }}
            >
              <p style={{ fontSize: 14, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                Scene {num}
              </p>
              <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, marginTop: 4 }}>
                {num === 1 && 'INT. COFFEE SHOP - DAY'}
                {num === 2 && 'EXT. CITY STREET - DAY'}
                {num === 3 && 'INT. APARTMENT - NIGHT'}
                {num === 4 && 'INT. OFFICE - DAY'}
                {num === 5 && 'EXT. PARK - SUNSET'}
              </p>
            </div>
          ))}
        </div>

        {/* Main Detail Panel */}
        <div
          style={{
            flex: 1,
            backgroundColor: '#1e293b',
            borderRadius: 12,
            padding: 30,
            opacity: detailFade,
          }}
        >
          {/* Scene Header */}
          <div style={{ marginBottom: 30 }}>
            <h3
              style={{
                fontSize: 32,
                color: '#f1f5f9',
                margin: 0,
                fontWeight: 700,
              }}
            >
              Scene 2
            </h3>
            <p style={{ fontSize: 18, color: '#fbbf24', marginTop: 8 }}>
              EXT. CITY STREET - DAY
            </p>
          </div>

          {/* Breakdown Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Characters */}
            <div
              style={{
                padding: 20,
                backgroundColor: '#0f172a',
                borderRadius: 8,
                border: '2px solid #334155',
                opacity: interpolate(frame, [90, 110], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Users size={20} color="#fbbf24" />
                <h4 style={{ fontSize: 16, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  Characters
                </h4>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {['SARAH', 'MIKE'].map((char) => (
                  <span
                    key={char}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#334155',
                      borderRadius: 6,
                      fontSize: 13,
                      color: '#f1f5f9',
                      fontWeight: 500,
                    }}
                  >
                    {char}
                  </span>
                ))}
              </div>
            </div>

            {/* Location */}
            <div
              style={{
                padding: 20,
                backgroundColor: '#0f172a',
                borderRadius: 8,
                border: '2px solid #334155',
                opacity: interpolate(frame, [100, 120], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <MapPin size={20} color="#10b981" />
                <h4 style={{ fontSize: 16, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  Location
                </h4>
              </div>
              <p style={{ fontSize: 14, color: '#94a3b8', margin: 0 }}>
                City Street (Exterior)
              </p>
            </div>

            {/* Time of Day */}
            <div
              style={{
                padding: 20,
                backgroundColor: '#0f172a',
                borderRadius: 8,
                border: '2px solid #334155',
                opacity: interpolate(frame, [110, 130], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Clock size={20} color="#3b82f6" />
                <h4 style={{ fontSize: 16, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  Time of Day
                </h4>
              </div>
              <p style={{ fontSize: 14, color: '#94a3b8', margin: 0 }}>
                Day
              </p>
            </div>

            {/* Props */}
            <div
              style={{
                padding: 20,
                backgroundColor: '#0f172a',
                borderRadius: 8,
                border: '2px solid #334155',
                opacity: interpolate(frame, [120, 140], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <Tag size={20} color="#a855f7" />
                <h4 style={{ fontSize: 16, color: '#f1f5f9', margin: 0, fontWeight: 600 }}>
                  Props
                </h4>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {['Coffee Cup', 'Briefcase', 'Phone'].map((prop) => (
                  <span
                    key={prop}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#334155',
                      borderRadius: 6,
                      fontSize: 13,
                      color: '#f1f5f9',
                    }}
                  >
                    {prop}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Highlight Badge */}
          {frame > 150 && (
            <div
              style={{
                marginTop: 30,
                padding: '16px 24px',
                backgroundColor: '#10b98120',
                border: '2px solid #10b981',
                borderRadius: 8,
                opacity: interpolate(frame, [150, 170], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
              }}
            >
              <p style={{ fontSize: 14, color: '#10b981', margin: 0, textAlign: 'center', fontWeight: 600 }}>
                ✨ All metadata extracted automatically by AI
              </p>
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
