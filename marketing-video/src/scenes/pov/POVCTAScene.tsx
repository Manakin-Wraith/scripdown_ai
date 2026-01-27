import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring, useVideoConfig } from 'remotion';
import { ArrowRight } from 'lucide-react';

export const POVCTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({
    frame,
    fps,
    config: { damping: 100, stiffness: 200 },
  });

  const buttonPulse = Math.sin(frame / 10) * 0.05 + 1;

  const urlOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Main CTA */}
      <div
        style={{
          transform: `scale(${titleScale})`,
          textAlign: 'center',
        }}
      >
        <h2
          style={{
            fontSize: 56,
            fontWeight: 700,
            background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            margin: 0,
            marginBottom: 24,
          }}
        >
          Ready to Transform
        </h2>
        <h2
          style={{
            fontSize: 56,
            fontWeight: 700,
            color: '#f1f5f9',
            margin: 0,
            marginBottom: 40,
          }}
        >
          Your Pre-Production?
        </h2>

        {/* CTA Button */}
        <button
          style={{
            padding: '20px 48px',
            fontSize: 24,
            fontWeight: 700,
            color: '#0f172a',
            background: 'linear-gradient(90deg, #fbbf24, #f59e0b)',
            border: 'none',
            borderRadius: 12,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 12,
            transform: `scale(${buttonPulse})`,
            boxShadow: '0 10px 40px rgba(251, 191, 36, 0.4)',
          }}
        >
          Start Free Trial
          <ArrowRight size={28} />
        </button>

        {/* Benefits */}
        <div
          style={{
            marginTop: 40,
            display: 'flex',
            gap: 40,
            justifyContent: 'center',
          }}
        >
          {['14-Day Free Trial', 'No Credit Card', 'Full Access'].map((benefit) => (
            <div key={benefit} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  backgroundColor: '#10b981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 12,
                  color: '#0f172a',
                  fontWeight: 700,
                }}
              >
                ✓
              </div>
              <span style={{ fontSize: 16, color: '#94a3b8' }}>{benefit}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Website URL */}
      <div
        style={{
          position: 'absolute',
          bottom: 80,
          opacity: urlOpacity,
        }}
      >
        <p
          style={{
            fontSize: 32,
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
