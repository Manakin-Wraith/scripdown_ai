import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

export const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Main CTA scale animation
  const ctaScale = spring({
    frame: frame - 10,
    fps,
    config: {
      damping: 100,
      stiffness: 200,
    },
  });

  // Button pulse animation
  const buttonScale = 1 + Math.sin(frame / 15) * 0.05;

  // Text fade in
  const textOpacity = interpolate(
    frame,
    [20, 50],
    [0, 1],
    {
      extrapolateRight: 'clamp',
    }
  );

  // URL fade in
  const urlOpacity = interpolate(
    frame,
    [60, 90],
    [0, 1],
    {
      extrapolateRight: 'clamp',
    }
  );

  // Features list stagger
  const feature1Opacity = interpolate(frame, [40, 60], [0, 1], { extrapolateRight: 'clamp' });
  const feature2Opacity = interpolate(frame, [50, 70], [0, 1], { extrapolateRight: 'clamp' });
  const feature3Opacity = interpolate(frame, [60, 80], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
      }}
    >
      {/* Animated background */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          opacity: 0.2,
          background: `
            radial-gradient(circle at 20% 30%, #fbbf24 0%, transparent 40%),
            radial-gradient(circle at 80% 70%, #f59e0b 0%, transparent 40%)
          `,
        }}
      />

      {/* Main CTA */}
      <div
        style={{
          transform: `scale(${ctaScale})`,
          marginBottom: 60,
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            fontSize: 96,
            fontWeight: 800,
            margin: 0,
            marginBottom: 24,
            background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.02em',
          }}
        >
          Start Your Free Trial
        </h1>
        <p
          style={{
            fontSize: 42,
            color: '#f1f5f9',
            margin: 0,
            opacity: textOpacity,
          }}
        >
          Transform Your Pre-Production Today
        </p>
      </div>

      {/* Features checklist */}
      <div
        style={{
          marginBottom: 60,
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        <div style={{ opacity: feature1Opacity, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: '#22c55e',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
            }}
          >
            ✓
          </div>
          <span style={{ fontSize: 32, color: '#cbd5e1' }}>14-Day Free Trial</span>
        </div>
        <div style={{ opacity: feature2Opacity, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: '#22c55e',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
            }}
          >
            ✓
          </div>
          <span style={{ fontSize: 32, color: '#cbd5e1' }}>No Credit Card Required</span>
        </div>
        <div style={{ opacity: feature3Opacity, display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              background: '#22c55e',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
            }}
          >
            ✓
          </div>
          <span style={{ fontSize: 32, color: '#cbd5e1' }}>Full Feature Access</span>
        </div>
      </div>

      {/* CTA Button */}
      <div
        style={{
          transform: `scale(${buttonScale})`,
          marginBottom: 40,
        }}
      >
        <div
          style={{
            padding: '24px 80px',
            borderRadius: 16,
            background: 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)',
            fontSize: 48,
            fontWeight: 700,
            color: '#0f172a',
            boxShadow: '0 20px 60px rgba(251, 191, 36, 0.5)',
            cursor: 'pointer',
          }}
        >
          Get Started Now
        </div>
      </div>

      {/* Website URL */}
      <div
        style={{
          opacity: urlOpacity,
        }}
      >
        <p
          style={{
            fontSize: 36,
            color: '#94a3b8',
            margin: 0,
            fontWeight: 500,
          }}
        >
          www.slateone.studio
        </p>
      </div>
    </AbsoluteFill>
  );
};
