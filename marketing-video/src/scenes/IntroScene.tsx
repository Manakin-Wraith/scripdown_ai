import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

interface IntroSceneProps {
  title: string;
  subtitle: string;
}

export const IntroScene: React.FC<IntroSceneProps> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Logo animation
  const logoScale = spring({
    frame: frame - 10,
    fps,
    config: {
      damping: 100,
      stiffness: 200,
      mass: 0.5,
    },
  });

  // Title slide in from left
  const titleX = interpolate(
    frame,
    [20, 50],
    [-width, 0],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Subtitle fade in
  const subtitleOpacity = interpolate(
    frame,
    [60, 90],
    [0, 1],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Tagline fade in
  const taglineOpacity = interpolate(
    frame,
    [100, 130],
    [0, 1],
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
      }}
    >
      {/* Animated background particles */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: 0.1,
          background: `radial-gradient(circle at ${interpolate(frame, [0, 150], [20, 80])}% ${interpolate(frame, [0, 150], [30, 70])}%, #fbbf24 0%, transparent 50%)`,
        }}
      />

      {/* Logo/Icon */}
      <div
        style={{
          transform: `scale(${logoScale})`,
          marginBottom: 60,
        }}
      >
        <div
          style={{
            width: 120,
            height: 120,
            borderRadius: 24,
            background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 64,
            boxShadow: '0 20px 60px rgba(251, 191, 36, 0.4)',
          }}
        >
          🎬
        </div>
      </div>

      {/* Title */}
      <div
        style={{
          transform: `translateX(${titleX}px)`,
          marginBottom: 24,
        }}
      >
        <h1
          style={{
            fontSize: 96,
            fontWeight: 800,
            margin: 0,
            background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}
        >
          {title}
        </h1>
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subtitleOpacity,
          marginBottom: 40,
        }}
      >
        <h2
          style={{
            fontSize: 48,
            fontWeight: 600,
            margin: 0,
            color: '#f1f5f9',
            letterSpacing: '-0.01em',
          }}
        >
          {subtitle}
        </h2>
      </div>

      {/* Tagline */}
      <div
        style={{
          opacity: taglineOpacity,
        }}
      >
        <p
          style={{
            fontSize: 32,
            color: '#94a3b8',
            margin: 0,
            textAlign: 'center',
            maxWidth: 800,
            lineHeight: 1.5,
          }}
        >
          Powered by AI • Built for Filmmakers
        </p>
      </div>
    </AbsoluteFill>
  );
};
