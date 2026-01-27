import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

interface FeatureSceneProps {
  title: string;
  description: string;
  icon: string;
  delay?: number;
}

export const FeatureScene: React.FC<FeatureSceneProps> = ({
  title,
  description,
  icon,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  // Icon entrance animation
  const iconScale = spring({
    frame: frame - delay,
    fps,
    config: {
      damping: 80,
      stiffness: 180,
    },
  });

  const iconRotate = interpolate(
    frame - delay,
    [0, 30],
    [0, 360],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Title slide in
  const titleY = interpolate(
    frame - delay,
    [15, 45],
    [100, 0],
    {
      extrapolateRight: 'clamp',
    }
  );

  const titleOpacity = interpolate(
    frame - delay,
    [15, 45],
    [0, 1],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Description fade in
  const descOpacity = interpolate(
    frame - delay,
    [45, 75],
    [0, 1],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Decorative elements
  const lineWidth = interpolate(
    frame - delay,
    [60, 90],
    [0, 400],
    {
      extrapolateRight: 'clamp',
    }
  );

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
        padding: '0 120px',
      }}
    >
      {/* Animated background glow */}
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 800,
          height: 800,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(251, 191, 36, 0.15) 0%, transparent 70%)',
          opacity: interpolate(frame - delay, [0, 60], [0, 1], { extrapolateRight: 'clamp' }),
        }}
      />

      {/* Icon */}
      <div
        style={{
          transform: `scale(${iconScale}) rotate(${iconRotate}deg)`,
          marginBottom: 60,
        }}
      >
        <div
          style={{
            width: 160,
            height: 160,
            borderRadius: 32,
            background: 'linear-gradient(135deg, #334155 0%, #1e293b 100%)',
            border: '4px solid #fbbf24',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 80,
            boxShadow: '0 20px 60px rgba(251, 191, 36, 0.3)',
          }}
        >
          {icon}
        </div>
      </div>

      {/* Decorative line */}
      <div
        style={{
          width: lineWidth,
          height: 4,
          background: 'linear-gradient(90deg, transparent 0%, #fbbf24 50%, transparent 100%)',
          marginBottom: 40,
        }}
      />

      {/* Title */}
      <div
        style={{
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
          marginBottom: 32,
        }}
      >
        <h2
          style={{
            fontSize: 72,
            fontWeight: 700,
            margin: 0,
            color: '#f1f5f9',
            textAlign: 'center',
            letterSpacing: '-0.02em',
          }}
        >
          {title}
        </h2>
      </div>

      {/* Description */}
      <div
        style={{
          opacity: descOpacity,
        }}
      >
        <p
          style={{
            fontSize: 36,
            color: '#94a3b8',
            margin: 0,
            textAlign: 'center',
            maxWidth: 1200,
            lineHeight: 1.6,
            fontWeight: 400,
          }}
        >
          {description}
        </p>
      </div>

      {/* Accent dots */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          display: 'flex',
          gap: 16,
          opacity: descOpacity,
        }}
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: i === 1 ? '#fbbf24' : '#475569',
            }}
          />
        ))}
      </div>
    </AbsoluteFill>
  );
};
